"""Detect line tactics from a board position."""

from __future__ import annotations

from collections.abc import Iterable

import chess

from tactix.LineTacticContext import LineTacticContext

BOARD_SQUARES = 64
_STEP_RULES = {
    1: (1, 0),
    -1: (1, 0),
    8: (0, 1),
    -8: (0, 1),
    7: (1, 1),
    -7: (1, 1),
    9: (1, 1),
    -9: (1, 1),
}
_LINE_PIECES_TARGET = 2


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
    if not _is_square_in_bounds(next_square):
        return None
    if not _matches_step_rule(square, next_square, step):
        return None
    return chess.Square(next_square)


def _is_square_in_bounds(square: int) -> bool:
    return 0 <= square < BOARD_SQUARES


def _matches_step_rule(
    square: chess.Square,
    next_square: int,
    step: int,
) -> bool:
    expected = _STEP_RULES.get(step)
    if expected is None:
        return False
    expected_file, expected_rank = expected
    file_diff = abs(chess.square_file(next_square) - chess.square_file(square))
    rank_diff = abs(chess.square_rank(next_square) - chess.square_rank(square))
    return file_diff == expected_file and rank_diff == expected_rank


def _iter_line_pieces(
    board: chess.Board,
    start: chess.Square,
    step: int,
) -> Iterable[chess.Piece]:
    current = start
    while True:
        next_square = _step_square(current, step)
        if next_square is None:
            return
        current = next_square
        piece = board.piece_at(current)
        if piece is not None:
            yield piece


def _find_two_opponent_pieces(
    board: chess.Board,
    start: chess.Square,
    step: int,
    opponent: bool,
) -> tuple[chess.Piece | None, chess.Piece | None]:
    found: list[chess.Piece] = []
    for piece in _iter_line_pieces(board, start, step):
        if piece.color != opponent:
            return None, None
        found.append(piece)
        if len(found) == _LINE_PIECES_TARGET:
            return found[0], found[1]
    return None, None
