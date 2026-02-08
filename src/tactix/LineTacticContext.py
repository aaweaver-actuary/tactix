"""Context for line tactic evaluations."""

# pylint: disable=invalid-name

from __future__ import annotations

from dataclasses import dataclass

import chess

from tactix.BaseTacticDetector import BaseTacticDetector


@dataclass(frozen=True)
class LineTacticContext:
    """Inputs for detecting line tactics such as pins or skewers."""

    detector: BaseTacticDetector
    board: chess.Board
    start: chess.Square
    step: int
    opponent: bool
    target_stronger: bool
