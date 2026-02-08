from __future__ import annotations

from importlib import import_module

from tactix.GameRow import GameRow
from tactix.should_skip_backfill__pipeline import _should_skip_backfill


def _filter_backfill_games(
    conn,
    rows: list[GameRow],
    source: str,
) -> tuple[list[GameRow], list[GameRow]]:
    if not rows:
        return [], []
    game_ids = [row["game_id"] for row in rows]
    pipeline_module = import_module("tactix.pipeline")
    latest_hashes = pipeline_module.fetch_latest_pgn_hashes(conn, game_ids, source)
    position_counts = pipeline_module.fetch_position_counts(conn, game_ids, source)
    to_process: list[GameRow] = []
    skipped: list[GameRow] = []
    for game in rows:
        if _should_skip_backfill(game, latest_hashes, position_counts):
            skipped.append(game)
        else:
            to_process.append(game)
    return to_process, skipped
