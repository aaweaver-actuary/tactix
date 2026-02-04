"""Filter games to a requested time window."""

from __future__ import annotations

from tactix.define_pipeline_state__pipeline import GameRow
from tactix.filter_games_by_window__pipeline import _filter_games_by_window


def _filter_games_for_window(
    games: list[GameRow],
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> tuple[list[GameRow], int]:
    """Return filtered games and the count removed."""
    pre_window_count = len(games)
    filtered = _filter_games_by_window(games, window_start_ms, window_end_ms)
    return filtered, pre_window_count - len(filtered)
