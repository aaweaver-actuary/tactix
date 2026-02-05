from __future__ import annotations

from tactix.filter_backfill_games__pipeline import _filter_backfill_games
from tactix.GameRow import GameRow


def _apply_backfill_filter(
    conn,
    games: list[GameRow],
    backfill_mode: bool,
    source: str,
) -> tuple[list[GameRow], list[GameRow]]:
    if not backfill_mode:
        return games, []
    return _filter_backfill_games(conn, games, source)
