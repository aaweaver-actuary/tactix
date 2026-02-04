"""Detect pins along a set of steps."""

from __future__ import annotations

import chess

from tactix._is_line_tactic import _is_line_tactic
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.LineTacticContext import LineTacticContext


def _has_pin_in_steps(
    detector: BaseTacticDetector,
    board: chess.Board,
    start: chess.Square,
    steps: tuple[int, ...],
    opponent: bool,
) -> bool:
    """Return True when any step produces a pin pattern."""
    for step in steps:
        if _is_line_tactic(LineTacticContext(detector, board, start, step, opponent, False)):
            return True
    return False
