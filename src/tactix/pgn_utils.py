from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Iterable
from collections.abc import Mapping

import chess.pgn

SITE_PATTERNS = [
    re.compile(r"lichess\.org/([A-Za-z0-9]{8})"),
    re.compile(r"chess\.com/(?:game/live|game|live/game)/(\d+)", re.IGNORECASE),
    re.compile(r"chess\.com/.*/(\d{6,})", re.IGNORECASE),
]

FIXTURE_SPLIT_RE = re.compile(r"\n{2,}(?=\[Event )")


def split_pgn_chunks(text: str) -> list[str]:
    return [chunk.strip() for chunk in FIXTURE_SPLIT_RE.split(text) if chunk.strip()]


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
    active_logger = logger or logging.getLogger(__name__)
    if not path.exists():
        active_logger.warning(missing_message, path)
        return []

    chunks = split_pgn_chunks(path.read_text())
    games: list[dict[str, object]] = []
    for raw in chunks:
        last_ts = extract_last_timestamp_ms(raw)
        if since_ms and last_ts <= since_ms:
            continue
        if until_ms is not None and last_ts >= until_ms:
            continue
        games.append(
            {
                "game_id": extract_game_id(raw),
                "user": user,
                "source": source,
                "fetched_at": datetime.now(timezone.utc),
                "pgn": raw,
                "last_timestamp_ms": last_ts,
            }
        )

    active_logger.info(loaded_message, len(games), path)
    return games


def extract_game_id(pgn: str) -> str:
    game = chess.pgn.read_game(StringIO(pgn))
    if game:
        site = game.headers.get("Site", "")
        for pattern in SITE_PATTERNS:
            match = pattern.search(site)
            if match:
                return match.group(1)
        if site:
            sanitized = re.sub(r"[^A-Za-z0-9]+", "", site)
            if sanitized:
                return sanitized[-16:]
    return str(abs(hash(pgn)))


def extract_last_timestamp_ms(pgn: str) -> int:
    game = chess.pgn.read_game(StringIO(pgn))
    if not game:
        return int(time.time() * 1000)
    utc_date = game.headers.get("UTCDate")
    utc_time = game.headers.get("UTCTime")
    if utc_date and utc_time:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"):
            try:
                dt = datetime.strptime(f"{utc_date} {utc_time}", fmt).replace(
                    tzinfo=timezone.utc
                )
                return int(dt.timestamp() * 1000)
            except ValueError:
                continue
    return int(time.time() * 1000)


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
    exporter = chess.pgn.StringExporter(
        headers=True, variations=True, comments=True, columns=80
    )
    normalized = game.accept(exporter)
    return normalized.strip()


def _parse_utc_start_ms(utc_date: str | None, utc_time: str | None) -> int | None:
    if not utc_date or not utc_time:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"):
        try:
            dt = datetime.strptime(f"{utc_date} {utc_time}", fmt).replace(
                tzinfo=timezone.utc
            )
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    return None


def extract_pgn_metadata(pgn: str, user: str) -> dict[str, object]:
    if not pgn.strip().startswith("["):
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
    game = chess.pgn.read_game(StringIO(pgn))
    if not game or getattr(game, "errors", None):
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
    headers = game.headers
    time_control = _normalize_header_value(headers.get("TimeControl"))
    white = _normalize_header_value(headers.get("White", ""))
    black = _normalize_header_value(headers.get("Black", ""))
    white_elo = _parse_elo(headers.get("WhiteElo"))
    black_elo = _parse_elo(headers.get("BlackElo"))
    user_lower = user.lower()
    white_lower = (white or "").lower()
    black_lower = (black or "").lower()
    rating = None
    if white_lower == user_lower:
        rating = white_elo
    elif black_lower == user_lower:
        rating = black_elo
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
