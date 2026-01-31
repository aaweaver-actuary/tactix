from __future__ import annotations

from tactix.pipeline_state__pipeline import GameRow
from tactix.should_skip_backfill__pipeline import _should_skip_backfill


def _filter_backfill_games(
    conn,
    rows: list[GameRow],
    source: str,
) -> tuple[list[GameRow], list[GameRow]]:
    if not rows:
        return [], []
    from tactix import pipeline as pipeline_module  # noqa: PLC0415

    game_ids = [row["game_id"] for row in rows]
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
