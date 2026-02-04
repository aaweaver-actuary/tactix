"""Check if a discovered line reveals a new target."""

from __future__ import annotations

import chess

from tactix.BaseTacticDetector import BaseTacticDetector


def _has_new_target(
    detector: BaseTacticDetector,
    board_before: chess.Board,
    board_after: chess.Board,
    square: chess.Square,
    opponent: bool,
) -> bool:
    """Return True when a new high-value target appears after the move."""
    return detector.has_high_value_target(
        board_after, square, opponent
    ) and not detector.has_high_value_target(board_before, square, opponent)
