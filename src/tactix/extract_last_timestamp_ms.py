"""Extract timestamp metadata from PGN strings."""

import re
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from io import StringIO

import chess.pgn

from tactix._parse_utc_start_ms import _parse_utc_start_ms


def extract_last_timestamp_ms(pgn: str) -> int:
    """Return the last timestamp in milliseconds for a PGN."""
    game = chess.pgn.read_game(StringIO(pgn))
    if not game:
        return int(time.time() * 1000)
    timestamp_ms = _parse_utc_header_timestamp(game.headers)
    if timestamp_ms is not None:
        return timestamp_ms
    return _parse_date_header_timestamp(game.headers)


def _parse_utc_header_timestamp(headers: Mapping[str, str]) -> int | None:
    utc_date = headers.get("UTCDate")
    utc_time = headers.get("UTCTime")
    timestamp_ms = _parse_utc_start_ms(utc_date, utc_time)
    if not timestamp_ms:
        return None
    return timestamp_ms


def _parse_date_header_timestamp(headers: Mapping[str, str]) -> int:
    date_value = headers.get("Date")
    end_time = headers.get("EndTime")
    if not date_value:
        return int(time.time() * 1000)
    try:
        dt = _parse_date_time_value(date_value, end_time)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return int(time.time() * 1000)


def _parse_date_time_value(date_value: str, end_time: str | None) -> datetime:
    time_match = re.search(r"(\d{2}:\d{2}:\d{2})", end_time or "")
    if time_match:
        return datetime.strptime(
            f"{date_value} {time_match.group(1)}",
            "%Y.%m.%d %H:%M:%S",
        ).replace(tzinfo=UTC)
    return datetime.strptime(date_value, "%Y.%m.%d").replace(tzinfo=UTC)
