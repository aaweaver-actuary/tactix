"""Build position dictionaries from PGN nodes."""

from dataclasses import dataclass

import chess
import chess.pgn

from tactix._position_context_helpers import (
    PositionContextInputs,
    _build_position_context,
    _is_illegal_move,
    _should_skip_for_side,
    _should_skip_for_turn,
    _side_from_turn,
    logger,
)
from tactix._push_and_none import _push_and_none
from tactix.PgnContext import PgnContext


@dataclass(frozen=True)
class PositionNodeInputs:
    """Inputs required to build a position from a node."""

    ctx: PgnContext
    game: chess.pgn.Game
    board: chess.Board
    user_color: bool
    side_filter: str | None
    node: chess.pgn.ChildNode


def _position_from_node(
    inputs: PositionNodeInputs,
) -> dict[str, object] | None:
    """Return a position dict for the given PGN node."""
    move = inputs.node.move
    if move is None:
        return None
    if _should_skip_for_turn(inputs.board, inputs.user_color):
        _push_and_none(inputs.board, move)
        return None
    side_to_move = _side_from_turn(inputs.board.turn)
    if _should_skip_for_side(side_to_move, inputs.side_filter):
        _push_and_none(inputs.board, move)
        return None
    if _is_illegal_move(inputs.board, move):
        logger.warning("Illegal move %s for FEN %s", move.uci(), inputs.board.fen())
        _push_and_none(inputs.board, move)
        return None
    position = _build_position_context(
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
