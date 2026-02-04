"""Locate the opponent king square."""

from __future__ import annotations

import chess


def _opponent_king_square(board: chess.Board, mover_color: bool) -> chess.Square | None:
    """Return the opponent king square if present."""
    return board.king(not mover_color)
