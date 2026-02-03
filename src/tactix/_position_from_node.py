import chess
import chess.pgn

from tactix._position_context_helpers import (
    _build_position_context,
    _is_illegal_move,
    _should_skip_for_side,
    _should_skip_for_turn,
    _side_from_turn,
    logger,
)
from tactix._push_and_none import _push_and_none
from tactix.PgnContext import PgnContext


def _position_from_node(
    ctx: PgnContext,
    game: chess.pgn.Game,
    board: chess.Board,
    user_color: bool,
    side_filter: str | None,
    node: chess.pgn.ChildNode,
) -> dict[str, object] | None:
    move = node.move
    if move is None:
        return None
    if _should_skip_for_turn(board, user_color):
        return _push_and_none(board, move)
    side_to_move = _side_from_turn(board.turn)
    if _should_skip_for_side(side_to_move, side_filter):
        return _push_and_none(board, move)
    if _is_illegal_move(board, move):
        logger.warning("Illegal move %s for FEN %s", move.uci(), board.fen())
        return _push_and_none(board, move)
    position = _build_position_context(ctx, game, board, node, move, side_to_move)
    board.push(move)
    return position
