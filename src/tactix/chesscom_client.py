from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import requests

from tactix.config import Settings
from tactix.logging_utils import get_logger
from tactix.pgn_utils import extract_game_id, extract_last_timestamp_ms, split_pgn_chunks

logger = get_logger(__name__)

ARCHIVES_URL = "https://api.chess.com/pub/player/{username}/games/archives"


def _auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


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


def _fetch_remote_games(settings: Settings, since_ms: int) -> List[dict]:
    url = ARCHIVES_URL.format(username=settings.user)
    try:
        archives_resp = requests.get(url, headers=_auth_headers(settings.chesscom_token), timeout=15)
        archives_resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falling back to fixtures; archive fetch failed: %s", exc)
        return _load_fixture_games(settings, since_ms)

    archives = archives_resp.json().get("archives", [])
    if not archives:
        logger.info("No archives returned for %s", settings.user)
        return []

    games: List[dict] = []
    # iterate newest to oldest but stop once we cross the checkpoint
    for archive_url in reversed(archives[-6:]):
        try:
            data = requests.get(
                archive_url,
                headers=_auth_headers(settings.chesscom_token),
                timeout=20,
            ).json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch archive %s: %s", archive_url, exc)
            continue

        archive_games = data.get("games", [])
        archive_max_ts = 0
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
            games.append(
                {
                    "game_id": str(game_id),
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


def fetch_incremental_games(settings: Settings, since_ms: int) -> List[dict]:
    if not settings.chesscom_token and settings.chesscom_use_fixture_when_no_token:
        return _load_fixture_games(settings, since_ms)
    return _fetch_remote_games(settings, since_ms)
