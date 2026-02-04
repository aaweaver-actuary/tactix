"""Identify candidate skewer source squares."""

from __future__ import annotations

import chess

ORTHOGONAL_STEPS = (1, -1, 8, -8)
DIAGONAL_STEPS = (7, -7, 9, -9)


def _skewer_sources(
    board: chess.Board,
    mover_color: bool,
) -> list[tuple[chess.Square, tuple[int, ...]]]:
    """Return slider squares and steps for skewer detection."""
    sources: list[tuple[chess.Square, tuple[int, ...]]] = []
    for square, piece in board.piece_map().items():
        if piece.color != mover_color:
            continue
        if piece.piece_type == chess.ROOK:
            sources.append((square, ORTHOGONAL_STEPS))
        elif piece.piece_type == chess.BISHOP:
            sources.append((square, DIAGONAL_STEPS))
        elif piece.piece_type == chess.QUEEN:
            sources.append((square, ORTHOGONAL_STEPS + DIAGONAL_STEPS))
    return sources
