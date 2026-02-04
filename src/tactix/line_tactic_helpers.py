"""Helpers for constructing line tactic contexts."""

from dataclasses import dataclass

import chess

from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.LineTacticContext import LineTacticContext
from tactix.utils.logger import funclogger


@dataclass(frozen=True)
class LineTacticInputs:
    """Grouped inputs for line tactic contexts."""

    detector: BaseTacticDetector
    board: chess.Board
    start: chess.Square
    step: int
    opponent: bool
    target_stronger: bool


@funclogger
def build_line_tactic_context(inputs: LineTacticInputs) -> LineTacticContext:
    """Build a LineTacticContext for line tactic checks."""
    return LineTacticContext(
        detector=inputs.detector,
        board=inputs.board,
        start=inputs.start,
        step=inputs.step,
        opponent=inputs.opponent,
        target_stronger=inputs.target_stronger,
    )
