"""Identify candidate skewer source squares."""

from __future__ import annotations

import chess

ORTHOGONAL_STEPS = (1, -1, 8, -8)
DIAGONAL_STEPS = (7, -7, 9, -9)
SKEWER_PIECE_STEPS = {
    chess.ROOK: ORTHOGONAL_STEPS,
    chess.BISHOP: DIAGONAL_STEPS,
    chess.QUEEN: ORTHOGONAL_STEPS + DIAGONAL_STEPS,
}


def _skewer_sources(
    board: chess.Board,
    mover_color: bool,
) -> list[tuple[chess.Square, tuple[int, ...]]]:
    """Return slider squares and steps for skewer detection."""
    sources: list[tuple[chess.Square, tuple[int, ...]]] = []
    for square, piece in board.piece_map().items():
        if piece.color != mover_color:
            continue
        steps = SKEWER_PIECE_STEPS.get(piece.piece_type)
        if steps is not None:
            sources.append((square, steps))
    return sources
