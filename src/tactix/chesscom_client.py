from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import List, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
import time

import requests

from tactix.config import Settings
from tactix.logging_utils import get_logger
from tactix.pgn_utils import (
    extract_game_id,
    extract_last_timestamp_ms,
    latest_timestamp,
    split_pgn_chunks,
)

logger = get_logger(__name__)

ARCHIVES_URL = "https://api.chess.com/pub/player/{username}/games/archives"


@dataclass(slots=True)
class ChesscomFetchResult:
    games: List[dict]
    next_cursor: str | None
    last_timestamp_ms: int


def _auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value)
        return max(seconds, 0.0)
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = (dt - datetime.now(timezone.utc)).total_seconds()
            return max(delta, 0.0)
        except Exception:  # noqa: BLE001
            return None


def _get_with_backoff(settings: Settings, url: str, timeout: int) -> requests.Response:
    max_retries = max(settings.chesscom_max_retries, 0)
    base_backoff = max(settings.chesscom_retry_backoff_ms, 0) / 1000.0
    attempt = 0
    while True:
        response = requests.get(
            url, headers=_auth_headers(settings.chesscom_token), timeout=timeout
        )
        if response.status_code != 429:
            response.raise_for_status()
            return response
        retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        if attempt >= max_retries:
            response.raise_for_status()
        wait_seconds = max(base_backoff * (2**attempt), retry_after or 0.0)
        logger.warning(
            "Chess.com rate limited (429). Retrying in %.2fs (attempt %s/%s).",
            wait_seconds,
            attempt + 1,
            max_retries,
        )
        if wait_seconds:
            time.sleep(wait_seconds)
        attempt += 1


def _parse_cursor(cursor: str | None) -> Tuple[int, str]:
    if not cursor:
        return 0, ""
    if ":" in cursor:
        prefix, suffix = cursor.split(":", 1)
        try:
            return int(prefix), suffix
        except ValueError:
            return 0, cursor
    if cursor.isdigit():
        return int(cursor), ""
    return 0, cursor


def _build_cursor(last_ts: int, game_id: str) -> str:
    return f"{last_ts}:{game_id}"


def read_cursor(path: Path) -> str | None:
    try:
        raw = path.read_text().strip()
    except FileNotFoundError:
        return None
    return raw or None


def write_cursor(path: Path, cursor: str | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if cursor is None:
        path.write_text("")
        return
    path.write_text(cursor)


def _load_fixture_games(settings: Settings, since_ms: int) -> List[dict]:
    path = settings.chesscom_fixture_pgn_path
    if not path.exists():
        logger.warning("Chess.com fixture PGN path missing: %s", path)
        return []

    games: List[dict] = []
    for raw in split_pgn_chunks(path.read_text()):
        last_ts = extract_last_timestamp_ms(raw)
        if since_ms and last_ts <= since_ms:
            continue
        games.append(
            {
                "game_id": extract_game_id(raw),
                "user": settings.user,
                "source": settings.source,
                "fetched_at": datetime.now(timezone.utc),
                "pgn": raw,
                "last_timestamp_ms": last_ts,
            }
        )

    logger.info("Loaded %s Chess.com fixture PGNs from %s", len(games), path)
    return games


def _next_page_url(data: dict, current_url: str) -> str | None:
    for key in ("next_page", "next", "next_url", "nextPage"):
        candidate = data.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
        if isinstance(candidate, dict):
            href = candidate.get("href") or candidate.get("url")
            if href:
                return href

    page = _coerce_int(data.get("page") or data.get("current_page"))
    total_pages = _coerce_int(data.get("total_pages") or data.get("totalPages"))
    if page is not None and total_pages is not None and page < total_pages:
        parsed = urlparse(current_url)
        query = parse_qs(parsed.query)
        query["page"] = [str(page + 1)]
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    return None


def _coerce_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _fetch_archive_pages(settings: Settings, archive_url: str) -> List[dict]:
    games: List[dict] = []
    next_url: str | None = archive_url
    seen_urls: set[str] = set()

    while next_url:
        if next_url in seen_urls:
            logger.warning("Pagination loop detected for %s", archive_url)
            break
        seen_urls.add(next_url)

        data = _get_with_backoff(settings, next_url, timeout=20).json()
        games.extend(data.get("games", []))
        next_url = _next_page_url(data, next_url)

    return games


def _fetch_remote_games(
    settings: Settings, since_ms: int, *, full_history: bool = False
) -> List[dict]:
    url = ARCHIVES_URL.format(username=settings.user)
    try:
        archives_resp = _get_with_backoff(settings, url, timeout=15)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falling back to fixtures; archive fetch failed: %s", exc)
        return _load_fixture_games(settings, since_ms)

    archives = archives_resp.json().get("archives", [])
    if not archives:
        logger.info("No archives returned for %s", settings.user)
        return []

    games: List[dict] = []
    archives_to_fetch = archives if full_history else archives[-6:]
    # iterate newest to oldest but stop once we cross the checkpoint
    for archive_url in reversed(archives_to_fetch):
        try:
            archive_games = _fetch_archive_pages(settings, archive_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch archive %s: %s", archive_url, exc)
            continue

        archive_max_ts = 0
        seen_game_ids: set[str] = set()
        for game in archive_games:
            if game.get("time_class") != settings.chesscom_time_class:
                continue
            pgn = game.get("pgn")
            if not pgn:
                continue
            last_ts = extract_last_timestamp_ms(pgn)
            archive_max_ts = max(archive_max_ts, last_ts)
            if since_ms and last_ts <= since_ms:
                continue
            game_id = game.get("uuid") or extract_game_id(pgn)
            game_id_str = str(game_id)
            if game_id_str in seen_game_ids:
                continue
            seen_game_ids.add(game_id_str)
            games.append(
                {
                    "game_id": game_id_str,
                    "user": settings.user,
                    "source": settings.source,
                    "fetched_at": datetime.now(timezone.utc),
                    "pgn": pgn,
                    "last_timestamp_ms": last_ts,
                }
            )
        if since_ms and archive_max_ts and archive_max_ts <= since_ms:
            break

    logger.info("Fetched %s Chess.com PGNs", len(games))
    return games


def _filter_by_cursor(rows: List[dict], cursor: str | None) -> List[dict]:
    since_ts, since_game = _parse_cursor(cursor)
    filtered: List[dict] = []
    for game in sorted(rows, key=lambda g: int(g.get("last_timestamp_ms", 0))):
        last_ts = int(game.get("last_timestamp_ms", 0))
        game_id = str(game.get("game_id", ""))
        if since_ts and last_ts < since_ts:
            continue
        if since_ts and last_ts == since_ts and since_game:
            # ensure true increment when multiple games share a timestamp
            if game_id <= since_game:
                continue
        filtered.append(game)
    return filtered


def fetch_incremental_games(
    settings: Settings, cursor: str | None, *, full_history: bool = False
) -> ChesscomFetchResult:
    if not settings.chesscom_token and settings.chesscom_use_fixture_when_no_token:
        raw_games = _load_fixture_games(settings, since_ms=0)
    else:
        raw_games = _fetch_remote_games(settings, since_ms=0, full_history=full_history)

    games = _filter_by_cursor(raw_games, cursor)
    for game in games:
        game["cursor"] = _build_cursor(
            int(game.get("last_timestamp_ms", 0)), str(game.get("game_id", ""))
        )

    last_ts = latest_timestamp(games) or _parse_cursor(cursor)[0]
    next_cursor = None
    if games:
        newest = max(games, key=lambda g: int(g.get("last_timestamp_ms", 0)))
        next_cursor = _build_cursor(
            int(newest.get("last_timestamp_ms", 0)), str(newest.get("game_id", ""))
        )
    elif cursor:
        next_cursor = cursor

    logger.info(
        "Fetched %s Chess.com PGNs with cursor=%s next_cursor=%s",
        len(games),
        cursor,
        next_cursor,
    )
    return ChesscomFetchResult(
        games=games, next_cursor=next_cursor, last_timestamp_ms=last_ts
    )
