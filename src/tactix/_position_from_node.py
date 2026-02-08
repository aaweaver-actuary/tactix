"""Build position dictionaries from PGN nodes."""

from dataclasses import dataclass

import chess
import chess.pgn

from tactix._push_and_none import _push_and_none
from tactix.PgnContext import PgnContext
from tactix.position_context_builder import (
    DEFAULT_POSITION_CONTEXT_BUILDER,
    PositionContextInputs,
)


@dataclass(frozen=True)
class PositionNodeInputs:
    """Inputs required to build a position from a node."""

    ctx: PgnContext
    game: chess.pgn.Game
    board: chess.Board
    user_color: bool
    side_filter: str | None
    node: chess.pgn.ChildNode


_POSITION_CONTEXT_BUILDER = DEFAULT_POSITION_CONTEXT_BUILDER


def _position_from_node(
    inputs: PositionNodeInputs,
) -> dict[str, object] | None:
    """Return a position dict for the given PGN node."""
    move = inputs.node.move
    if move is None:
        return None
    if _POSITION_CONTEXT_BUILDER.should_skip_for_turn(inputs.board, inputs.user_color):
        _push_and_none(inputs.board, move)
        return None
    side_to_move = _POSITION_CONTEXT_BUILDER.side_from_turn(inputs.board.turn)
    if _POSITION_CONTEXT_BUILDER.should_skip_for_side(side_to_move, inputs.side_filter):
        _push_and_none(inputs.board, move)
        return None
    if _POSITION_CONTEXT_BUILDER.is_illegal_move(inputs.board, move):
        _POSITION_CONTEXT_BUILDER.log.warning(
            "Illegal move %s for FEN %s", move.uci(), inputs.board.fen()
        )
        _push_and_none(inputs.board, move)
        return None
    position = _POSITION_CONTEXT_BUILDER.build(
        PositionContextInputs(
            ctx=inputs.ctx,
            game=inputs.game,
            board=inputs.board,
            node=inputs.node,
            move=move,
            side_to_move=side_to_move,
        )
    )
    inputs.board.push(move)
    return position
