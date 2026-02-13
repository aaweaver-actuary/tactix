"""Extract positions from fetched game PGNs."""

from __future__ import annotations

from tactix.app.use_cases.pipeline_support import _resolve_side_to_move_filter
from tactix.build_post_move_positions__positions import (
    append_positions_with_post_moves,
)
from tactix.config import Settings
from tactix.db.position_repository_provider import insert_positions
from tactix.extract_positions__pgn import extract_positions
from tactix.GameRow import GameRow


def _extract_positions_from_games(
    conn,
    games_to_process: list[GameRow],
    settings: Settings,
) -> list[dict[str, object]]:
    side_to_move_filter = _resolve_side_to_move_filter(settings)
    positions: list[dict[str, object]] = []
    post_positions: list[dict[str, object]] = []
    for game in games_to_process:
        extracted = extract_positions(
            game["pgn"],
            settings.user,
            settings.source,
            game_id=game["game_id"],
            side_to_move_filter=side_to_move_filter,
        )
        append_positions_with_post_moves(
            positions,
            extracted,
            post_positions=post_positions,
        )
    positions_to_insert = positions + post_positions
    position_ids = insert_positions(conn, positions_to_insert)
    for pos, pos_id in zip(positions_to_insert, position_ids, strict=False):
        pos["position_id"] = pos_id
    return positions_to_insert
