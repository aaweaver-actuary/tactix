"""Determine if a piece can deliver a fork."""

from __future__ import annotations

import chess


def _is_fork_piece(piece: chess.Piece | None) -> bool:
    """Return True when the piece type can realistically fork."""
    if piece is None:
        return False
    return piece.piece_type in {
        chess.KNIGHT,
        chess.QUEEN,
        chess.ROOK,
        chess.BISHOP,
    }
