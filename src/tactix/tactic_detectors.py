from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass

import chess

MISSED_DELTA_THRESHOLD = -300
FAILED_ATTEMPT_THRESHOLD = -100
BOARD_EDGE = 7
MIN_FORK_TARGETS = 2
MIN_FORK_CHECK_TARGETS = 1
ORTHOGONAL_STEPS = (1, -1, 8, -8)
DIAGONAL_STEPS = (7, -7, 9, -9)
QUEEN_STEPS = ORTHOGONAL_STEPS + DIAGONAL_STEPS
HIGH_VALUE_PIECES = (
    chess.QUEEN,
    chess.ROOK,
    chess.BISHOP,
    chess.KNIGHT,
)
KING_THREAT_PIECES = (
    chess.KING,
    chess.QUEEN,
    chess.ROOK,
    chess.BISHOP,
    chess.KNIGHT,
)
PIECE_VALUES = {
    chess.KING: 10000,
    chess.QUEEN: 900,
    chess.ROOK: 500,
    chess.BISHOP: 300,
    chess.KNIGHT: 300,
    chess.PAWN: 100,
}


@dataclass(frozen=True)
class TacticContext:
    board_before: chess.Board
    board_after: chess.Board
    best_move: chess.Move
    mover_color: bool


class BaseTacticDetector(ABC):
    motif: str

    @abstractmethod
    def detect(self, context: TacticContext) -> bool:
        raise NotImplementedError

    @staticmethod
    def classify_result(
        best_move: str | None, user_move: str, base_cp: int, after_cp: int
    ) -> tuple[str, int]:
        delta = after_cp - base_cp
        if best_move and user_move == best_move:
            return "found", delta
        if delta <= MISSED_DELTA_THRESHOLD:
            return "missed", delta
        if delta <= FAILED_ATTEMPT_THRESHOLD:
            return "failed_attempt", delta
        return "unclear", delta

    @staticmethod
    def score_from_pov(score_cp: int, pov_color: bool, turn_color: bool) -> int:
        if turn_color == pov_color:
            return score_cp
        return -score_cp

    @staticmethod
    def piece_value(piece_type: int) -> int:
        return PIECE_VALUES.get(piece_type, 0)

    @staticmethod
    def iter_unchanged_sliders(
        board_before: chess.Board,
        board_after: chess.Board,
        mover_color: bool,
        exclude_square: chess.Square | None = None,
    ) -> Iterable[tuple[chess.Square, chess.Piece]]:
        """Yield unchanged sliding pieces for the mover from before to after."""
        slider_types = {chess.ROOK, chess.BISHOP, chess.QUEEN}
        for square, piece in board_after.piece_map().items():
            if piece.color != mover_color or piece.piece_type not in slider_types:
                continue
            if exclude_square is not None and square == exclude_square:
                continue
            piece_before = board_before.piece_at(square)
            if not piece_before or piece_before.color != mover_color:
                continue
            if piece_before.piece_type != piece.piece_type:
                continue
            yield square, piece

    @staticmethod
    def first_piece_in_direction(
        board: chess.Board, start: chess.Square, step: int
    ) -> chess.Square | None:
        file = chess.square_file(start)
        rank = chess.square_rank(start)
        deltas = {
            ORTHOGONAL_STEPS[0]: (1, 0),
            ORTHOGONAL_STEPS[1]: (-1, 0),
            ORTHOGONAL_STEPS[2]: (0, 1),
            ORTHOGONAL_STEPS[3]: (0, -1),
            DIAGONAL_STEPS[0]: (-1, 1),
            DIAGONAL_STEPS[1]: (1, -1),
            DIAGONAL_STEPS[2]: (1, 1),
            DIAGONAL_STEPS[3]: (-1, -1),
        }
        delta = deltas.get(step)
        if delta is None:
            return None
        df, dr = delta
        file += df
        rank += dr
        while 0 <= file <= BOARD_EDGE and 0 <= rank <= BOARD_EDGE:
            square = chess.square(file, rank)
            if board.piece_at(square):
                return square
            file += df
            rank += dr
        return None

    @staticmethod
    def count_high_value_targets(
        board_after: chess.Board, to_square: chess.Square, mover_color: bool
    ) -> int:
        targets = 0
        for sq in board_after.attacks(to_square):
            piece = board_after.piece_at(sq)
            if piece and piece.color != mover_color and piece.piece_type in HIGH_VALUE_PIECES:
                targets += 1
        return targets

    @staticmethod
    def attacked_high_value_targets(
        board: chess.Board, square: chess.Square, opponent: bool
    ) -> set[chess.Square]:
        targets: set[chess.Square] = set()
        for target_sq in board.attacks(square):
            piece = board.piece_at(target_sq)
            if piece and piece.color == opponent and piece.piece_type in KING_THREAT_PIECES:
                targets.add(target_sq)
        return targets

    @staticmethod
    def is_hanging_capture(
        board_before: chess.Board,
        board_after: chess.Board,
        best_move: chess.Move,
        mover_color: bool,
    ) -> bool:
        captured = board_before.piece_at(best_move.to_square)
        if not captured or captured.piece_type not in HIGH_VALUE_PIECES:
            return False
        if board_after.is_checkmate():
            return True
        opponent = not mover_color
        attackers = list(board_before.attackers(opponent, best_move.to_square))
        if not attackers:
            return True
        return all(board_before.is_pinned(opponent, sq) for sq in attackers)


class DiscoveredCheckDetector(BaseTacticDetector):
    motif = "discovered_check"

    def detect(self, context: TacticContext) -> bool:
        if not context.board_after.is_check():
            return False
        opponent = not context.mover_color
        king_square = context.board_after.king(opponent)
        if king_square is None:
            return False
        for square, _piece in self.iter_unchanged_sliders(
            context.board_before,
            context.board_after,
            context.mover_color,
            exclude_square=context.best_move.to_square,
        ):
            if king_square not in context.board_after.attacks(square):
                continue
            if king_square in context.board_before.attacks(square):
                continue
            return True
        return False


class DiscoveredAttackDetector(BaseTacticDetector):
    motif = "discovered_attack"

    def detect(self, context: TacticContext) -> bool:
        moved_piece = context.board_before.piece_at(context.best_move.from_square)
        opponent = not context.mover_color
        exclude_square = None
        if moved_piece and moved_piece.piece_type in {
            chess.ROOK,
            chess.BISHOP,
            chess.QUEEN,
        }:
            exclude_square = context.best_move.to_square
        for square, _piece in self.iter_unchanged_sliders(
            context.board_before,
            context.board_after,
            context.mover_color,
            exclude_square=exclude_square,
        ):
            before_targets = self.attacked_high_value_targets(
                context.board_before, square, opponent
            )
            after_targets = self.attacked_high_value_targets(context.board_after, square, opponent)
            if after_targets - before_targets:
                return True
        return False


class SkewerDetector(BaseTacticDetector):
    motif = "skewer"

    def detect(self, context: TacticContext) -> bool:
        opponent = not context.mover_color
        slider_steps = {
            chess.ROOK: ORTHOGONAL_STEPS,
            chess.BISHOP: DIAGONAL_STEPS,
            chess.QUEEN: QUEEN_STEPS,
        }
        for square, piece in context.board_after.piece_map().items():
            if piece.color != context.mover_color or piece.piece_type not in slider_steps:
                continue
            for step in slider_steps[piece.piece_type]:
                first = self.first_piece_in_direction(context.board_after, square, step)
                if first is None:
                    continue
                target = context.board_after.piece_at(first)
                if not target or target.color != opponent:
                    continue
                second = self.first_piece_in_direction(context.board_after, first, step)
                if second is None:
                    continue
                behind = context.board_after.piece_at(second)
                if not behind or behind.color != opponent:
                    continue
                if self.piece_value(target.piece_type) > self.piece_value(behind.piece_type):
                    return True
        return False


class HangingPieceDetector(BaseTacticDetector):
    motif = "hanging_piece"

    def detect(self, context: TacticContext) -> bool:
        if not context.board_before.is_capture(context.best_move):
            return False
        return self.is_hanging_capture(
            context.board_before,
            context.board_after,
            context.best_move,
            context.mover_color,
        )


class PinDetector(BaseTacticDetector):
    motif = "pin"

    def detect(self, context: TacticContext) -> bool:
        moved_piece = context.board_before.piece_at(context.best_move.from_square)
        if not moved_piece or moved_piece.color != context.mover_color:
            return False
        slider_steps = {
            chess.ROOK: ORTHOGONAL_STEPS,
            chess.BISHOP: DIAGONAL_STEPS,
            chess.QUEEN: QUEEN_STEPS,
        }
        steps = slider_steps.get(moved_piece.piece_type)
        if not steps:
            return False
        opponent = not context.mover_color
        start = context.best_move.to_square
        for step in steps:
            first = self.first_piece_in_direction(context.board_after, start, step)
            if first is None:
                continue
            target = context.board_after.piece_at(first)
            if not target or target.color != opponent:
                continue
            second = self.first_piece_in_direction(context.board_after, first, step)
            if second is None:
                continue
            behind = context.board_after.piece_at(second)
            if not behind or behind.color != opponent:
                continue
            if self.piece_value(behind.piece_type) > self.piece_value(target.piece_type):
                return True
        return False


class ForkDetector(BaseTacticDetector):
    motif = "fork"

    def detect(self, context: TacticContext) -> bool:
        piece = context.board_before.piece_at(context.best_move.from_square)
        if not piece or piece.piece_type not in HIGH_VALUE_PIECES:
            return False
        forks = self.count_high_value_targets(
            context.board_after, context.best_move.to_square, context.mover_color
        )
        if forks >= MIN_FORK_TARGETS:
            return True
        return forks >= MIN_FORK_CHECK_TARGETS and context.board_after.is_check()


class CaptureDetector(BaseTacticDetector):
    motif = "capture"

    def detect(self, context: TacticContext) -> bool:
        return context.board_before.is_capture(context.best_move)


class MateDetector(BaseTacticDetector):
    motif = "mate"

    def detect(self, context: TacticContext) -> bool:
        return context.board_after.is_checkmate()


class CheckDetector(BaseTacticDetector):
    motif = "check"

    def detect(self, context: TacticContext) -> bool:
        return context.board_after.is_check()


class EscapeDetector(BaseTacticDetector):
    motif = "escape"

    def detect(self, context: TacticContext) -> bool:
        return context.board_before.is_attacked_by(
            not context.mover_color, context.best_move.from_square
        ) and not context.board_before.is_attacked_by(
            not context.mover_color, context.best_move.to_square
        )


class MotifDetectorSuite:
    def __init__(self, detectors: Iterable[BaseTacticDetector]) -> None:
        self._detectors = tuple(detectors)

    def infer_motif(self, board: chess.Board, best_move: chess.Move | None) -> str:
        if best_move is None:
            return "initiative"
        mover_color = board.turn
        board_after = board.copy()
        board_after.push(best_move)
        context = TacticContext(
            board_before=board,
            board_after=board_after,
            best_move=best_move,
            mover_color=mover_color,
        )
        for detector in self._detectors:
            if detector.detect(context):
                return detector.motif
        return "initiative"


def build_default_motif_detector_suite() -> MotifDetectorSuite:
    return MotifDetectorSuite(
        [
            DiscoveredCheckDetector(),
            DiscoveredAttackDetector(),
            SkewerDetector(),
            HangingPieceDetector(),
            PinDetector(),
            ForkDetector(),
            CaptureDetector(),
            MateDetector(),
            CheckDetector(),
            EscapeDetector(),
        ]
    )
