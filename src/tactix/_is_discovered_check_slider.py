"""Check whether a slider delivers a discovered check."""

from __future__ import annotations

import chess


def _is_discovered_check_slider(
    board_after: chess.Board,
    square: chess.Square,
    king_square: chess.Square,
) -> bool:
    """Return True when a slider attacks the king after a move."""
    piece = board_after.piece_at(square)
    if piece is None or piece.piece_type not in {chess.ROOK, chess.BISHOP, chess.QUEEN}:
        return False
    return board_after.is_attacked_by(piece.color, king_square)
