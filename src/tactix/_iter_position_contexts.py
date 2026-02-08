"""Iterate position contexts from a parsed PGN."""

import chess
import chess.pgn

from tactix._position_from_node import PositionNodeInputs, _position_from_node
from tactix.PgnContext import PgnContext


def _iter_position_contexts(
    ctx: PgnContext,
    game: chess.pgn.Game,
    board: chess.Board,
    user_color: bool,
    side_filter: str | None,
) -> list[dict[str, object]]:
    positions: list[dict[str, object]] = []
    for node in game.mainline():
        position = _position_from_node(
            PositionNodeInputs(
                ctx=ctx,
                game=game,
                board=board,
                user_color=user_color,
                side_filter=side_filter,
                node=node,
            )
        )
        if position is not None:
            positions.append(position)
    return positions
