from __future__ import annotations

from tactix.latest_timestamp import latest_timestamp
from tactix.pipeline_state__pipeline import GameRow


def _resolve_last_timestamp_value(games: list[GameRow], fallback: int) -> int:
    if not games:
        return fallback
    return latest_timestamp(games) or fallback
