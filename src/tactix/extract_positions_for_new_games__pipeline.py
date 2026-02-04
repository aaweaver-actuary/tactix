"""Extract positions for newly ingested games."""

from __future__ import annotations

from tactix.attach_position_ids__pipeline import _attach_position_ids
from tactix.collect_game_ids__pipeline import _collect_game_ids
from tactix.config import Settings
from tactix.db.duckdb_store import fetch_position_counts, insert_positions
from tactix.extract_positions_for_rows__pipeline import _extract_positions_for_rows
from tactix.filter_unprocessed_games__pipeline import _filter_unprocessed_games


def _extract_positions_for_new_games(
    conn, settings: Settings, raw_pgns: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[str]]:
    game_ids = _collect_game_ids(raw_pgns)
    if not game_ids:
        return [], []
    position_counts = fetch_position_counts(conn, game_ids, settings.source)
    to_process = _filter_unprocessed_games(raw_pgns, position_counts)
    if not to_process:
        return [], []
    positions = _extract_positions_for_rows(to_process, settings)
    position_ids = insert_positions(conn, positions)
    _attach_position_ids(positions, position_ids)
    return positions, _collect_game_ids(to_process)
