from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from io import StringIO
from typing import Iterable

import chess.pgn

SITE_PATTERNS = [
    re.compile(r"lichess\.org/([A-Za-z0-9]{8})"),
    re.compile(r"chess\.com/(?:game/live|game|live/game)/(\d+)", re.IGNORECASE),
    re.compile(r"chess\.com/.*/(\d{6,})", re.IGNORECASE),
]

FIXTURE_SPLIT_RE = re.compile(r"\n\n(?=\[Event )")


def split_pgn_chunks(text: str) -> list[str]:
    return [chunk.strip() for chunk in FIXTURE_SPLIT_RE.split(text) if chunk.strip()]


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


def latest_timestamp(rows: Iterable[dict]) -> int:
    ts = 0
    for row in rows:
        ts = max(ts, int(row.get("last_timestamp_ms", 0)))
    return ts
