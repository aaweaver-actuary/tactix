"""Resolve the capture square for a move, handling en passant."""

from __future__ import annotations

import chess


def _resolve_capture_square__move(
    board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if mover_color == chess.WHITE else 8)
    return move.to_square
