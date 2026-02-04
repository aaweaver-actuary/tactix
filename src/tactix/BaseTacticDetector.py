"""Base helpers for tactic detectors."""

# pylint: disable=invalid-name

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import chess

MISSED_DELTA_THRESHOLD = -300
FAILED_ATTEMPT_THRESHOLD = -100

PIECE_VALUES = {
    chess.KING: 10000,
    chess.QUEEN: 900,
    chess.ROOK: 500,
    chess.BISHOP: 300,
    chess.KNIGHT: 300,
    chess.PAWN: 100,
}

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


@dataclass(frozen=True)
class SliderInfo:
    """Describe a stationary slider piece."""

    square: chess.Square
    piece: chess.Piece


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
        if best_move is None:
            return "initiative", 0
        delta = after_cp - base_cp
        if user_move_uci == best_move:
            return "found", delta
        if delta <= MISSED_DELTA_THRESHOLD:
            return "missed", delta
        if delta <= FAILED_ATTEMPT_THRESHOLD:
            return "failed_attempt", delta
        return "unclear", delta

    @classmethod
    def has_hanging_piece(cls, board: chess.Board, mover_color: bool) -> bool:
        """Return True when the opponent has a hanging piece."""
        opponent = not mover_color
        for square, piece in board.piece_map().items():
            if piece.color != opponent:
                continue
            if board.is_attacked_by(mover_color, square) and not board.is_attacked_by(
                opponent, square
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
        result = False
        if board_after.is_checkmate():
            result = True
        else:
            capture_square = move.to_square
            if board_before.is_en_passant(move):
                capture_square = move.to_square + (-8 if mover_color == chess.WHITE else 8)
            captured_piece = board_before.piece_at(capture_square)
            if captured_piece is not None:
                if not board_before.is_attacked_by(not mover_color, capture_square):
                    result = True
                else:
                    mover_piece = board_before.piece_at(move.from_square)
                    if mover_piece is not None:
                        result = PIECE_VALUES.get(captured_piece.piece_type, 0) > PIECE_VALUES.get(
                            mover_piece.piece_type, 0
                        )
        return result

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
        attacks = board.attacks(square)
        total = 0
        for target in attacks:
            target_piece = board.piece_at(target)
            if target_piece is None or target_piece.color == mover_color:
                continue
            if target_piece.piece_type in HIGH_VALUE_PIECES:
                total += 1
        return total

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
        for target in board.attacks(square):
            target_piece = board.piece_at(target)
            if (
                target_piece
                and target_piece.color == opponent
                and target_piece.piece_type in HIGH_VALUE_PIECES
            ):
                return True
        return False

    def iter_unchanged_sliders(
        self,
        board_before: chess.Board,
        board_after: chess.Board,
        mover_color: bool,
        *,
        exclude_square: chess.Square | None = None,
    ) -> Iterable[tuple[chess.Square, chess.Piece]]:
        """Yield slider pieces that did not move between boards."""
        for square, piece in board_after.piece_map().items():
            if piece.color != mover_color or piece.piece_type not in SLIDER_PIECES:
                continue
            if exclude_square is not None and square == exclude_square:
                continue
            before_piece = board_before.piece_at(square)
            if before_piece is None or before_piece.piece_type != piece.piece_type:
                continue
            if before_piece.color != piece.color:
                continue
            yield square, piece
