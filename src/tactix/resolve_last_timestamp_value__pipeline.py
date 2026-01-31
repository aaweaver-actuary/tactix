from __future__ import annotations

from tactix.pipeline_state__pipeline import GameRow
from tactix.prepare_pgn__chess import latest_timestamp


def _resolve_last_timestamp_value(games: list[GameRow], fallback: int) -> int:
    if not games:
        return fallback
    return latest_timestamp(games) or fallback
