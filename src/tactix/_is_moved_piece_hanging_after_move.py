"""Detect whether the moved piece becomes hanging after a move."""

from __future__ import annotations

import chess

from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.utils.logger import funclogger


@funclogger
def _is_moved_piece_hanging_after_move(
    board_before: chess.Board,
    board_after: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> bool:
    moved_piece = board_before.piece_at(move.from_square)
    if moved_piece is None:
        return False
    target_square = move.to_square
    if not board_after.is_attacked_by(not mover_color, target_square):
        return False
    if not board_after.is_attacked_by(mover_color, target_square):
        return True
    for response in board_after.legal_moves:
        if not board_after.is_capture(response):
            continue
        capture_square = response.to_square
        if board_after.is_en_passant(response):
            capture_square = response.to_square + (-8 if board_after.turn == chess.WHITE else 8)
        if capture_square != target_square:
            continue
        responder_piece = board_after.piece_at(response.from_square)
        if responder_piece is None:
            continue
        if BaseTacticDetector.piece_value(moved_piece.piece_type) > BaseTacticDetector.piece_value(
            responder_piece.piece_type
        ):
            return True
    return False
