"""Detect tactical motifs from chess positions."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

from collections.abc import Iterable

import chess

from tactix._is_line_tactic import _is_line_tactic
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.CaptureDetector import CaptureDetector
from tactix.DiscoveredAttackDetector import DiscoveredAttackDetector
from tactix.DiscoveredCheckDetector import DiscoveredCheckDetector
from tactix.ForkDetector import ForkDetector
from tactix.HangingPieceDetector import HangingPieceDetector
from tactix.line_tactic_helpers import LineTacticInputs, build_line_tactic_context
from tactix.PinDetector import PinDetector
from tactix.SkewerDetector import SkewerDetector
from tactix.TacticContext import TacticContext

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


def _is_pin_in_step(
    detector: BaseTacticDetector,
    board: chess.Board,
    start: chess.Square,
    step: int,
    opponent: bool,
) -> bool:
    return _is_line_tactic(
        build_line_tactic_context(LineTacticInputs(detector, board, start, step, opponent, False))
    )


class MateDetector(BaseTacticDetector):
    """Detect checkmate tactics."""

    motif = "mate"

    def detect(self, context: TacticContext) -> bool:
        """Return True when the move delivers checkmate."""
        return context.board_after.is_checkmate()


class CheckDetector(BaseTacticDetector):
    """Detect checking moves."""

    motif = "check"

    def detect(self, context: TacticContext) -> bool:
        """Return True when the move gives check."""
        return context.board_after.is_check()


class EscapeDetector(BaseTacticDetector):
    """Detect escape tactics where a piece escapes attack."""

    motif = "escape"

    def detect(self, context: TacticContext) -> bool:
        """Return True when the moved piece escapes attack."""
        return context.board_before.is_attacked_by(
            not context.mover_color, context.best_move.from_square
        ) and not context.board_before.is_attacked_by(
            not context.mover_color, context.best_move.to_square
        )


class MotifDetectorSuite:
    """Collection of detectors used to infer a tactic motif."""

    def __init__(self, detectors: Iterable[BaseTacticDetector]) -> None:
        """Initialize the detector suite."""
        self._detectors = tuple(detectors)

    def infer_motif(self, board: chess.Board, best_move: chess.Move | None) -> str:
        """Infer the best motif label for a move on the given board."""
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
    """Build the default set of motif detectors."""
    return MotifDetectorSuite(
        [
            MateDetector(),
            DiscoveredAttackDetector(),
            SkewerDetector(),
            PinDetector(),
            ForkDetector(),
            DiscoveredCheckDetector(),
            HangingPieceDetector(),
            CaptureDetector(),
            CheckDetector(),
            EscapeDetector(),
        ]
    )


_VULTURE_USED = (BOARD_EDGE, SLIDER_STEPS, KING_THREAT_PIECES, _is_pin_in_step)
