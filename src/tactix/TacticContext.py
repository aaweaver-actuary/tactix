"""Context for tactic detector evaluation."""

# pylint: disable=invalid-name

from __future__ import annotations

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class TacticContext:
    """Inputs used by tactic detectors."""

    board_before: chess.Board
    board_after: chess.Board
    best_move: chess.Move
    mover_color: bool
