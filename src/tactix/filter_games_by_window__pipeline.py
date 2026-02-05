from __future__ import annotations

from tactix.GameRow import GameRow
from tactix.within_window__pipeline import _within_window


def _filter_games_by_window(
    rows: list[GameRow],
    start_ms: int | None,
    end_ms: int | None,
) -> list[GameRow]:
    if start_ms is None and end_ms is None:
        return rows
    return [game for game in rows if _within_window(game, start_ms, end_ms)]
