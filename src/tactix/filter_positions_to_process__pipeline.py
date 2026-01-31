from __future__ import annotations

from tactix.collect_game_ids__pipeline import _collect_game_ids
from tactix.config import Settings
from tactix.db.duckdb_store import fetch_position_counts
from tactix.filter_unprocessed_games__pipeline import _filter_unprocessed_games


def _filter_positions_to_process(
    conn,
    raw_pgns: list[dict[str, object]],
    settings: Settings,
) -> list[dict[str, object]]:
    game_ids = _collect_game_ids(raw_pgns)
    position_counts = fetch_position_counts(conn, game_ids, settings.source)
    return _filter_unprocessed_games(raw_pgns, position_counts)
