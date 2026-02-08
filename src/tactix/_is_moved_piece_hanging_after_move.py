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
    moved_piece = _moved_piece_after_move(board_after, move, mover_color)
    if moved_piece is None:
        moved_piece = _moved_piece_before_move(board_before, move)
    if moved_piece is None:
        return False
    return _is_hanging_after_move(board_after, move.to_square, moved_piece, mover_color)


def _moved_piece_after_move(
    board_after: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> chess.Piece | None:
    moved_piece = board_after.piece_at(move.to_square)
    if moved_piece is None or moved_piece.color != mover_color:
        return None
    return moved_piece


def _moved_piece_before_move(
    board_before: chess.Board,
    move: chess.Move,
) -> chess.Piece | None:
    return board_before.piece_at(move.from_square)


def _is_hanging_after_move(
    board_after: chess.Board,
    target_square: chess.Square,
    moved_piece: chess.Piece,
    mover_color: bool,
) -> bool:
    if not board_after.is_attacked_by(not mover_color, target_square):
        return False
    return _resolve_defended_hanging_after_move(
        board_after,
        target_square,
        moved_piece,
        mover_color,
    )


def _resolve_defended_hanging_after_move(
    board_after: chess.Board,
    target_square: chess.Square,
    moved_piece: chess.Piece,
    mover_color: bool,
) -> bool:
    if not board_after.is_attacked_by(mover_color, target_square):
        return True
    return BaseTacticDetector.is_favorable_trade_on_square(
        board_after,
        target_square,
        moved_piece,
        not mover_color,
    )
