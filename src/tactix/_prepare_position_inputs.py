"""Prepare analysis inputs from a position row."""

import chess

from tactix.utils.logger import funclogger


@funclogger
def _prepare_position_inputs(
    position: dict[str, object],
) -> tuple[str, str, chess.Board, chess.Board, bool]:
    """Return normalized analysis inputs from a position mapping."""
    fen = str(position["fen"])
    user_move_uci = str(position["uci"])
    board = chess.Board(fen)
    motif_board = board.copy()
    mover_color = board.turn
    return fen, user_move_uci, board, motif_board, mover_color
