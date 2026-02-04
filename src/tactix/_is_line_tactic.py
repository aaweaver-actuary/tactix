"""Detect line tactics from a board position."""

from __future__ import annotations

import chess

from tactix.LineTacticContext import LineTacticContext

BOARD_SQUARES = 64


def _is_line_tactic(context: LineTacticContext) -> bool:
    """Return True when two opponent pieces satisfy a line tactic."""
    first_piece, second_piece = _find_two_opponent_pieces(
        context.board,
        context.start,
        context.step,
        context.opponent,
    )

    if first_piece is None or second_piece is None:
        return False
    first_value = context.detector.piece_value(first_piece.piece_type)
    second_value = context.detector.piece_value(second_piece.piece_type)
    if context.target_stronger:
        return first_value > second_value
    return second_value > first_value


def _step_square(square: chess.Square, step: int) -> chess.Square | None:
    next_square = square + step
    if next_square < 0 or next_square >= BOARD_SQUARES:
        return None
    file_diff = abs(chess.square_file(next_square) - chess.square_file(square))
    rank_diff = abs(chess.square_rank(next_square) - chess.square_rank(square))
    if step in (1, -1) and rank_diff != 0:
        return None
    if step in (8, -8) and file_diff != 0:
        return None
    if step in (7, -7, 9, -9) and (file_diff != 1 or rank_diff != 1):
        return None
    return chess.Square(next_square)


def _find_two_opponent_pieces(
    board: chess.Board,
    start: chess.Square,
    step: int,
    opponent: bool,
) -> tuple[chess.Piece | None, chess.Piece | None]:
    current = start
    first_piece: chess.Piece | None = None
    while True:
        next_square = _step_square(current, step)
        if next_square is None:
            return None, None
        current = next_square
        piece = board.piece_at(current)
        if piece is None:
            continue
        if piece.color != opponent:
            return None, None
        if first_piece is None:
            first_piece = piece
            continue
        return first_piece, piece
