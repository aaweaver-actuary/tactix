"""Check whether a game falls within a time window."""

from __future__ import annotations

from tactix.GameRow import GameRow


def _within_window(game: GameRow, start_ms: int | None, end_ms: int | None) -> bool:
    last_ts = game["last_timestamp_ms"]
    return (start_ms is None or last_ts >= start_ms) and (end_ms is None or last_ts < end_ms)
