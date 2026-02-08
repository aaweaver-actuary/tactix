from __future__ import annotations

from collections.abc import Mapping

from tactix.db.raw_pgn_repository_provider import hash_pgn
from tactix.define_pipeline_state__pipeline import ZERO_COUNT
from tactix.GameRow import GameRow


def _should_skip_backfill(
    game: GameRow,
    latest_hashes: Mapping[str, str],
    position_counts: Mapping[str, int],
) -> bool:
    game_id = game["game_id"]
    current_hash = hash_pgn(game["pgn"])
    existing_hash = latest_hashes.get(game_id)
    return bool(
        existing_hash == current_hash and position_counts.get(game_id, ZERO_COUNT) > ZERO_COUNT
    )
