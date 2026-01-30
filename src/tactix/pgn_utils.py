from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import chess.pgn

from tactix.utils.logger import get_logger

SITE_PATTERNS = [
    re.compile(r"lichess\.org/([A-Za-z0-9]{8})"),
    re.compile(r"chess\.com/(?:game/live|game|live/game)/(\d+)", re.IGNORECASE),
    re.compile(r"chess\.com/.*/(\d{6,})", re.IGNORECASE),
]

FIXTURE_SPLIT_RE = re.compile(r"\n{2,}(?=\[Event )")


def split_pgn_chunks(text: str) -> list[str]:
    return [chunk.strip() for chunk in FIXTURE_SPLIT_RE.split(text) if chunk.strip()]


def _current_timestamp_ms() -> int:
    return int(time.time() * 1000)


def _should_include_fixture(
    last_ts: int,
    since_ms: int,
    until_ms: int | None,
) -> bool:
    if since_ms and last_ts <= since_ms:
        return False
    return not (until_ms is not None and last_ts >= until_ms)


def _fixture_payload(
    pgn: str,
    user: str,
    source: str,
    last_ts: int,
) -> dict[str, object]:
    return {
        "game_id": extract_game_id(pgn),
        "user": user,
        "source": source,
        "fetched_at": datetime.now(UTC),
        "pgn": pgn,
        "last_timestamp_ms": last_ts,
    }


def load_fixture_games(
    path: Path,
    user: str,
    source: str,
    since_ms: int,
    *,
    until_ms: int | None = None,
    logger: logging.Logger | None = None,
    missing_message: str = "Fixture PGN path missing: %s",
    loaded_message: str = "Loaded %s fixture PGNs from %s",
) -> list[dict[str, object]]:
    """Load fixture PGNs from disk and apply since/until timestamp filters."""
    active_logger = logger or get_logger(__name__)
    if not path.exists():
        active_logger.warning(missing_message, path)
        return []
    chunks = split_pgn_chunks(path.read_text())
    games = _filter_fixture_games(chunks, user, source, since_ms, until_ms)
    active_logger.info(loaded_message, len(games), path)
    return games


def _filter_fixture_games(
    chunks: list[str],
    user: str,
    source: str,
    since_ms: int,
    until_ms: int | None,
) -> list[dict[str, object]]:
    games: list[dict[str, object]] = []
    for raw in chunks:
        last_ts = extract_last_timestamp_ms(raw)
        if not _should_include_fixture(last_ts, since_ms, until_ms):
            continue
        games.append(_fixture_payload(raw, user, source, last_ts))
    return games


def extract_game_id(pgn: str) -> str:
    game = chess.pgn.read_game(StringIO(pgn))
    return _extract_site_id(game) or str(abs(hash(pgn)))


def _extract_site_id(game: chess.pgn.Game | None) -> str | None:
    if not game:
        return None
    site = game.headers.get("Site", "")
    return _match_site_id(site)


def _match_site_id(site: str) -> str | None:
    for pattern in SITE_PATTERNS:
        match = pattern.search(site)
        if match:
            return match.group(1)
    if site:
        sanitized = re.sub(r"[^A-Za-z0-9]+", "", site)
        if sanitized:
            return sanitized[-16:]
    return None


def extract_last_timestamp_ms(pgn: str) -> int:
    game = chess.pgn.read_game(StringIO(pgn))
    if not game:
        return _current_timestamp_ms()
    utc_date = game.headers.get("UTCDate")
    utc_time = game.headers.get("UTCTime")
    return _parse_utc_start_ms(utc_date, utc_time) or _current_timestamp_ms()


def _parse_elo(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _normalize_header_value(value: str | None) -> str | None:
    if not value:
        return None
    if value.strip() == "?":
        return None
    return value


def normalize_pgn(pgn: str) -> str:
    game = chess.pgn.read_game(StringIO(pgn))
    if not game:
        return pgn.strip()
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=80)
    normalized = game.accept(exporter)
    return normalized.strip()


def _parse_utc_start_ms(utc_date: str | None, utc_time: str | None) -> int | None:
    if not utc_date or not utc_time:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"):
        try:
            dt = datetime.strptime(f"{utc_date} {utc_time}", fmt).replace(tzinfo=UTC)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    return None


def _empty_pgn_metadata() -> dict[str, object]:
    return {
        "user_rating": None,
        "time_control": None,
        "white_player": None,
        "black_player": None,
        "white_elo": None,
        "black_elo": None,
        "result": None,
        "event": None,
        "site": None,
        "utc_date": None,
        "utc_time": None,
        "termination": None,
        "start_timestamp_ms": None,
    }


def _resolve_user_rating(
    user: str,
    white: str | None,
    black: str | None,
    white_elo: int | None,
    black_elo: int | None,
) -> int | None:
    user_lower = user.lower()
    white_lower = (white or "").lower()
    black_lower = (black or "").lower()
    if white_lower == user_lower:
        return white_elo
    if black_lower == user_lower:
        return black_elo
    return None


def extract_pgn_metadata(pgn: str, user: str) -> dict[str, object]:
    if not pgn.strip().startswith("["):
        return _empty_pgn_metadata()
    game = chess.pgn.read_game(StringIO(pgn))
    if not game or getattr(game, "errors", None):
        return _empty_pgn_metadata()
    return _extract_metadata_from_headers(game.headers, user)


def _extract_metadata_from_headers(
    headers: Mapping[str, str],
    user: str,
) -> dict[str, object]:
    time_control = _normalize_header_value(headers.get("TimeControl"))
    white = _normalize_header_value(headers.get("White", ""))
    black = _normalize_header_value(headers.get("Black", ""))
    white_elo = _parse_elo(headers.get("WhiteElo"))
    black_elo = _parse_elo(headers.get("BlackElo"))
    rating = _resolve_user_rating(user, white, black, white_elo, black_elo)
    utc_date = _normalize_header_value(headers.get("UTCDate"))
    utc_time = _normalize_header_value(headers.get("UTCTime"))
    return {
        "user_rating": rating,
        "time_control": time_control,
        "white_player": white,
        "black_player": black,
        "white_elo": white_elo,
        "black_elo": black_elo,
        "result": _normalize_header_value(headers.get("Result")),
        "event": _normalize_header_value(headers.get("Event")),
        "site": _normalize_header_value(headers.get("Site")),
        "utc_date": utc_date,
        "utc_time": utc_time,
        "termination": _normalize_header_value(headers.get("Termination")),
        "start_timestamp_ms": _parse_utc_start_ms(utc_date, utc_time),
    }


def latest_timestamp(rows: Iterable[Mapping[str, object]]) -> int:
    ts = 0
    for row in rows:
        value = row.get("last_timestamp_ms", 0)
        if isinstance(value, (int, float, bool)):
            current = int(value)
        elif isinstance(value, str):
            try:
                current = int(value)
            except ValueError:
                current = 0
        else:
            current = 0
        ts = max(ts, current)
    return ts
