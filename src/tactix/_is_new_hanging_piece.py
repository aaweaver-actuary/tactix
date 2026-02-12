"""Detect whether a move creates a new hanging piece."""

import chess

from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.utils.logger import funclogger


@funclogger
def _is_new_hanging_piece(
    board_before: chess.Board,
    board_after: chess.Board,
    mover_color: bool,
) -> bool:
    """Return True if a hanging piece appears after the move."""
    opponent = not mover_color

    def opponent_has_hanging_piece(board: chess.Board) -> bool:
        for square, piece in board.piece_map().items():
            if piece.color != opponent:
                continue
            if BaseTacticDetector.has_legal_capture_on_square(
                board,
                square,
                mover_color,
            ) and not BaseTacticDetector.has_legal_capture_on_square(
                board,
                square,
                opponent,
            ):
                return True
        return False

    if opponent_has_hanging_piece(board_before):
        return False
    return opponent_has_hanging_piece(board_after)
