"""Base helpers for tactic detectors."""

from __future__ import annotations

from collections.abc import Iterable

import chess
from pydantic import BaseModel

PIECE_VALUES = {
    chess.KING: 10000,
    chess.QUEEN: 900,
    chess.ROOK: 500,
    chess.BISHOP: 300,
    chess.KNIGHT: 300,
    chess.PAWN: 100,
}

MISSED_DELTA_THRESHOLD = -300
FAILED_ATTEMPT_THRESHOLD = -100

HIGH_VALUE_PIECES = {
    chess.QUEEN,
    chess.ROOK,
    chess.BISHOP,
    chess.KNIGHT,
    chess.KING,
}

SLIDER_PIECES = {
    chess.ROOK,
    chess.BISHOP,
    chess.QUEEN,
}


def _capture_square_for_move(
    board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if mover_color == chess.WHITE else 8)
    return move.to_square


def _classify_no_best_move(delta: int) -> str:
    if delta <= MISSED_DELTA_THRESHOLD:
        return "missed"
    if delta <= FAILED_ATTEMPT_THRESHOLD:
        return "failed_attempt"
    return "initiative"


def _classify_with_best_move(user_move_uci: str, best_move: str, delta: int) -> str:
    if user_move_uci == best_move:
        return "found"
    if delta <= MISSED_DELTA_THRESHOLD:
        return "missed"
    if delta <= FAILED_ATTEMPT_THRESHOLD:
        return "failed_attempt"
    return "unclear"


def _iter_opponent_targets(
    board: chess.Board,
    square: chess.Square,
    mover_color: bool,
) -> Iterable[chess.Piece]:
    for target in board.attacks(square):
        target_piece = board.piece_at(target)
        if target_piece and target_piece.color != mover_color:
            yield target_piece


def _is_unchanged_slider(
    board_before: chess.Board,
    square: chess.Square,
    piece: chess.Piece,
) -> bool:
    before_piece = board_before.piece_at(square)
    if before_piece is None:
        return False
    if before_piece.piece_type != piece.piece_type:
        return False
    return before_piece.color == piece.color


def _is_slider_candidate(
    piece: chess.Piece,
    mover_color: bool,
    square: chess.Square,
    exclude_square: chess.Square | None,
) -> bool:
    if piece.color != mover_color or piece.piece_type not in SLIDER_PIECES:
        return False
    if exclude_square is None:
        return True
    return square != exclude_square


def _iter_unchanged_sliders(
    board_before: chess.Board,
    board_after: chess.Board,
    mover_color: bool,
    exclude_square: chess.Square | None,
) -> Iterable[tuple[chess.Square, chess.Piece]]:
    for square, piece in board_after.piece_map().items():
        if not _is_slider_candidate(piece, mover_color, square, exclude_square):
            continue
        if _is_unchanged_slider(board_before, square, piece):
            yield square, piece


def _can_compare_capture(
    mover_piece: chess.Piece | None,
    board_after: chess.Board,
) -> bool:
    if mover_piece is None:
        return False
    return not board_after.is_checkmate()


def _is_favorable_trade(captured_piece: chess.Piece, mover_piece: chess.Piece) -> bool:
    return PIECE_VALUES.get(captured_piece.piece_type, 0) > PIECE_VALUES.get(
        mover_piece.piece_type, 0
    )


class PieceInfo(BaseModel):
    """Describe a piece on the board."""

    square: chess.Square
    piece: chess.Piece


class SliderInfo(PieceInfo):
    """Describe a stationary slider piece."""


class BaseTacticDetector:
    """Base class providing shared tactic helper logic."""

    motif = "unknown"

    def detect(self, _context: object) -> bool:
        """Return True when the tactic is detected."""
        raise NotImplementedError

    @staticmethod
    def piece_value(piece_type: int) -> int:
        """Return the material value for a piece type."""
        return PIECE_VALUES.get(piece_type, 0)

    @staticmethod
    def score_from_pov(score_cp: int, mover_color: bool, board_turn: bool) -> int:
        """Normalize a score to the mover's perspective."""
        return score_cp if mover_color == board_turn else -score_cp

    @classmethod
    def classify_result(
        cls,
        best_move: str | None,
        user_move_uci: str,
        base_cp: int,
        after_cp: int,
    ) -> tuple[str, int]:
        """Classify the tactic result based on evaluation swing."""
        delta = after_cp - base_cp
        if best_move is None:
            return _classify_no_best_move(delta), delta
        return _classify_with_best_move(user_move_uci, best_move, delta), delta

    @classmethod
    def has_hanging_piece(cls, board: chess.Board, mover_color: bool) -> bool:
        """Return True when the mover has a hanging piece."""
        opponent = not mover_color
        for square, piece in board.piece_map().items():
            if piece.color != mover_color:
                continue
            if board.is_attacked_by(opponent, square) and not board.is_attacked_by(
                mover_color, square
            ):
                return True
        return False

    @classmethod
    def is_hanging_capture(
        cls,
        board_before: chess.Board,
        board_after: chess.Board,
        move: chess.Move,
        mover_color: bool,
    ) -> bool:
        """Return True when a capture removes a hanging piece."""
        if not board_before.is_capture(move):
            return False
        capture_square = _capture_square_for_move(board_before, move, mover_color)
        captured_piece = board_before.piece_at(capture_square)
        if captured_piece is None:
            return False
        if not board_before.is_attacked_by(not mover_color, capture_square):
            return True
        mover_piece = board_before.piece_at(move.from_square)
        if not _can_compare_capture(mover_piece, board_after):
            return False
        return _is_favorable_trade(captured_piece, mover_piece)

    @classmethod
    def count_high_value_targets(
        cls,
        board: chess.Board,
        square: chess.Square,
        mover_color: bool,
    ) -> int:
        """Count high-value opponent targets attacked from a square."""
        piece = board.piece_at(square)
        if piece is None or piece.color != mover_color:
            return 0
        return sum(
            1
            for target_piece in _iter_opponent_targets(board, square, mover_color)
            if target_piece.piece_type in HIGH_VALUE_PIECES
        )

    @classmethod
    def has_high_value_target(
        cls,
        board: chess.Board,
        square: chess.Square,
        opponent: bool,
    ) -> bool:
        """Return True when a square attacks a high-value opponent piece."""
        piece = board.piece_at(square)
        if piece is None or piece.color == opponent:
            return False
        return any(
            target_piece.piece_type in HIGH_VALUE_PIECES
            for target_piece in _iter_opponent_targets(board, square, not opponent)
        )

    @classmethod
    def iter_unchanged_sliders(
        cls,
        board_before: chess.Board,
        board_after: chess.Board,
        mover_color: bool,
        *,
        exclude_square: chess.Square | None = None,
    ) -> Iterable[tuple[chess.Square, chess.Piece]]:
        """Yield slider pieces that did not move between boards."""
        yield from _iter_unchanged_sliders(
            board_before,
            board_after,
            mover_color,
            exclude_square,
        )


_VULTURE_USED = (
    SliderInfo,
    BaseTacticDetector.has_hanging_piece,
    BaseTacticDetector.has_high_value_target,
)
