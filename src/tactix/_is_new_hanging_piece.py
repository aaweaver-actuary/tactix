"""Detect whether a move creates a new hanging piece."""

import chess

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
            if board.is_attacked_by(mover_color, square) and not board.is_attacked_by(
                opponent, square
            ):
                return True
        return False

    if opponent_has_hanging_piece(board_before):
        return False
    return opponent_has_hanging_piece(board_after)
