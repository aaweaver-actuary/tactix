"""Resolve last timestamp values for pipeline steps."""

from __future__ import annotations

from tactix.GameRow import GameRow
from tactix.latest_timestamp import latest_timestamp


def _resolve_last_timestamp_value(games: list[GameRow], fallback: int) -> int:
    """Return the last timestamp from games or a fallback value."""
    if not games:
        return fallback
    return latest_timestamp(games) or fallback
