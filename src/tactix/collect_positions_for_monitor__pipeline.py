from __future__ import annotations

from tactix.config import Settings
from tactix.db.duckdb_store import fetch_unanalyzed_positions
from tactix.extract_positions_for_new_games__pipeline import _extract_positions_for_new_games


def _collect_positions_for_monitor(
    conn,
    settings: Settings,
    raw_pgns: list[dict[str, object]],
) -> tuple[int, list[str], list[dict[str, object]]]:
    positions_extracted = 0
    new_game_ids: list[str] = []
    if raw_pgns:
        extracted_positions, new_game_ids = _extract_positions_for_new_games(
            conn, settings, raw_pgns
        )
        positions_extracted = len(extracted_positions)

    positions_to_analyze: list[dict[str, object]] = []
    if new_game_ids:
        positions_to_analyze = fetch_unanalyzed_positions(
            conn, game_ids=new_game_ids, source=settings.source
        )

    return positions_extracted, new_game_ids, positions_to_analyze
