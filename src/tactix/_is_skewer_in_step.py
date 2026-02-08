"""Detect a skewer along a single step."""

import chess

from tactix._is_line_tactic import _is_line_tactic
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.line_tactic_context_builder import (
    DEFAULT_LINE_TACTIC_CONTEXT_BUILDER,
    LineTacticContextInputs,
)
from tactix.utils.logger import funclogger


@funclogger
def _is_skewer_in_step(  # pragma: no cover
    detector: BaseTacticDetector,
    board: chess.Board,
    start: chess.Square,
    step: int,
    opponent: bool,
) -> bool:
    return _is_line_tactic(
        DEFAULT_LINE_TACTIC_CONTEXT_BUILDER.build(
            LineTacticContextInputs(detector, board, start, step, opponent, True)
        )
    )


_VULTURE_USED = (_is_skewer_in_step,)
