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
SLIDER_STEPS = {
    chess.ROOK: ORTHOGONAL_STEPS,
    chess.BISHOP: DIAGONAL_STEPS,
    chess.QUEEN: QUEEN_STEPS,
}
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
            if not _is_slider_piece(piece, mover_color, slider_types):
                continue
            if _is_excluded_square(square, exclude_square):
                continue
            piece_before = board_before.piece_at(square)
            if not _matches_before_piece(piece_before, piece, mover_color):
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
        if not _is_high_value_capture(captured):
            return False
        if board_after.is_checkmate():
            return True
        opponent = not mover_color
        attackers = _attackers_to_square(board_before, opponent, best_move.to_square)
        if not attackers:
            return True
        return _attackers_are_pinned(board_before, opponent, attackers)


def _is_slider_piece(piece: chess.Piece, mover_color: bool, slider_types: set[int]) -> bool:
    return piece.color == mover_color and piece.piece_type in slider_types


def _is_excluded_square(square: chess.Square, exclude_square: chess.Square | None) -> bool:
    return bool(exclude_square is not None and square == exclude_square)


def _matches_before_piece(
    piece_before: chess.Piece | None, piece: chess.Piece, mover_color: bool
) -> bool:
    if not piece_before or piece_before.color != mover_color:
        return False
    return piece_before.piece_type == piece.piece_type


def _is_high_value_capture(captured: chess.Piece | None) -> bool:
    return bool(captured and captured.piece_type in HIGH_VALUE_PIECES)


def _attackers_to_square(
    board: chess.Board, attacker_color: bool, square: chess.Square
) -> list[chess.Square]:
    return list(board.attackers(attacker_color, square))


def _attackers_are_pinned(
    board: chess.Board, attacker_color: bool, attackers: Iterable[chess.Square]
) -> bool:
    return all(board.is_pinned(attacker_color, sq) for sq in attackers)


def _opponent_king_square(board: chess.Board, mover_color: bool) -> chess.Square | None:
    opponent = not mover_color
    return board.king(opponent)


def _has_discovered_check(
    detector: BaseTacticDetector,
    board_before: chess.Board,
    board_after: chess.Board,
    mover_color: bool,
    king_square: chess.Square,
    exclude_square: chess.Square,
) -> bool:
    for square, _piece in detector.iter_unchanged_sliders(
        board_before,
        board_after,
        mover_color,
        exclude_square=exclude_square,
    ):
        if _is_discovered_check_slider(board_before, board_after, square, king_square):
            return True
    return False


def _is_discovered_check_slider(
    board_before: chess.Board,
    board_after: chess.Board,
    square: chess.Square,
    king_square: chess.Square,
) -> bool:
    if king_square not in board_after.attacks(square):
        return False
    return king_square not in board_before.attacks(square)


def _has_discovered_attack(
    detector: BaseTacticDetector,
    board_before: chess.Board,
    board_after: chess.Board,
    mover_color: bool,
    opponent: bool,
    exclude_square: chess.Square | None,
) -> bool:
    for square, _piece in detector.iter_unchanged_sliders(
        board_before,
        board_after,
        mover_color,
        exclude_square=exclude_square,
    ):
        if _has_new_target(detector, board_before, board_after, square, opponent):
            return True
    return False


def _has_new_target(
    detector: BaseTacticDetector,
    board_before: chess.Board,
    board_after: chess.Board,
    square: chess.Square,
    opponent: bool,
) -> bool:
    before_targets = detector.attacked_high_value_targets(board_before, square, opponent)
    after_targets = detector.attacked_high_value_targets(board_after, square, opponent)
    return bool(after_targets - before_targets)


class DiscoveredCheckDetector(BaseTacticDetector):
    motif = "discovered_check"

    def detect(self, context: TacticContext) -> bool:
        if not context.board_after.is_check():
            return False
        king_square = _opponent_king_square(context.board_after, context.mover_color)
        if king_square is None:
            return False
        return _has_discovered_check(
            self,
            context.board_before,
            context.board_after,
            context.mover_color,
            king_square,
            context.best_move.to_square,
        )


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
        return _has_discovered_attack(
            self,
            context.board_before,
            context.board_after,
            context.mover_color,
            opponent,
            exclude_square,
        )


class SkewerDetector(BaseTacticDetector):
    motif = "skewer"

    def detect(self, context: TacticContext) -> bool:
        opponent = not context.mover_color
        return any(
            _has_skewer_in_steps(self, context.board_after, square, steps, opponent)
            for square, steps in _skewer_sources(context.board_after, context.mover_color)
        )


def _skewer_sources(
    board: chess.Board, mover_color: bool
) -> Iterable[tuple[chess.Square, Iterable[int]]]:
    for square, piece in board.piece_map().items():
        steps = SLIDER_STEPS.get(piece.piece_type)
        if piece.color != mover_color or not steps:
            continue
        yield square, steps


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
        steps = SLIDER_STEPS.get(moved_piece.piece_type)
        if not steps:
            return False
        opponent = not context.mover_color
        return _has_pin_in_steps(
            self,
            context.board_after,
            context.best_move.to_square,
            steps,
            opponent,
        )


def _has_skewer_in_steps(
    detector: BaseTacticDetector,
    board: chess.Board,
    start: chess.Square,
    steps: Iterable[int],
    opponent: bool,
) -> bool:
    return any(_is_skewer_in_step(detector, board, start, step, opponent) for step in steps)


def _is_skewer_in_step(
    detector: BaseTacticDetector,
    board: chess.Board,
    start: chess.Square,
    step: int,
    opponent: bool,
) -> bool:
    pieces = _two_pieces_in_line(detector, board, start, step)
    if pieces is None:
        return False
    target, behind = pieces
    if not _is_opponent_piece(target, opponent) or not _is_opponent_piece(behind, opponent):
        return False
    return detector.piece_value(target.piece_type) > detector.piece_value(behind.piece_type)


def _has_pin_in_steps(
    detector: BaseTacticDetector,
    board: chess.Board,
    start: chess.Square,
    steps: Iterable[int],
    opponent: bool,
) -> bool:
    return any(_is_pin_in_step(detector, board, start, step, opponent) for step in steps)


def _is_pin_in_step(
    detector: BaseTacticDetector,
    board: chess.Board,
    start: chess.Square,
    step: int,
    opponent: bool,
) -> bool:
    pieces = _two_pieces_in_line(detector, board, start, step)
    if pieces is None:
        return False
    target, behind = pieces
    if not _is_opponent_piece(target, opponent) or not _is_opponent_piece(behind, opponent):
        return False
    return detector.piece_value(behind.piece_type) > detector.piece_value(target.piece_type)


def _is_opponent_piece(piece: chess.Piece | None, opponent: bool) -> bool:
    return bool(piece) and piece.color == opponent


def _two_pieces_in_line(
    detector: BaseTacticDetector,
    board: chess.Board,
    start: chess.Square,
    step: int,
) -> tuple[chess.Piece, chess.Piece] | None:
    first = detector.first_piece_in_direction(board, start, step)
    if first is None:
        return None
    second = detector.first_piece_in_direction(board, first, step)
    if second is None:
        return None
    target = board.piece_at(first)
    behind = board.piece_at(second)
    if target is None or behind is None:
        return None
    return target, behind


class ForkDetector(BaseTacticDetector):
    motif = "fork"

    def detect(self, context: TacticContext) -> bool:
        piece = context.board_before.piece_at(context.best_move.from_square)
        if not _is_fork_piece(piece):
            return False
        forks = self.count_high_value_targets(
            context.board_after, context.best_move.to_square, context.mover_color
        )
        return _forks_meet_threshold(forks, context.board_after)


def _is_fork_piece(piece: chess.Piece | None) -> bool:
    return bool(piece) and piece.piece_type in HIGH_VALUE_PIECES


def _forks_meet_threshold(forks: int, board_after: chess.Board) -> bool:
    if forks >= MIN_FORK_TARGETS:
        return True
    return forks >= MIN_FORK_CHECK_TARGETS and board_after.is_check()


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
