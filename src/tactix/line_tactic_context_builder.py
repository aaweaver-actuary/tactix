"""Build line tactic contexts with an object-based API."""

# pylint: disable=too-few-public-methods

from dataclasses import dataclass

import chess

from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.LineTacticContext import LineTacticContext
from tactix.utils.logger import funclogger


@dataclass(frozen=True)
class LineTacticContextInputs:
    """Grouped inputs for line tactic contexts."""

    detector: BaseTacticDetector
    board: chess.Board
    start: chess.Square
    step: int
    opponent: bool
    target_stronger: bool


class LineTacticContextBuilder:
    """Construct LineTacticContext instances for line tactics."""

    @funclogger
    def build(self, inputs: LineTacticContextInputs) -> LineTacticContext:
        """Build a LineTacticContext for line tactic checks."""
        return LineTacticContext(
            detector=inputs.detector,
            board=inputs.board,
            start=inputs.start,
            step=inputs.step,
            opponent=inputs.opponent,
            target_stronger=inputs.target_stronger,
        )


DEFAULT_LINE_TACTIC_CONTEXT_BUILDER = LineTacticContextBuilder()
