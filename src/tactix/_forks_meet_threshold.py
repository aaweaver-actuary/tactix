"""Check fork targets against thresholds."""

from __future__ import annotations

import chess

MIN_FORK_TARGETS = 2
MIN_FORK_CHECK_TARGETS = 1


def _forks_meet_threshold(forks: int, board: chess.Board) -> bool:
    """Return True when forks meet the target threshold."""
    threshold = MIN_FORK_CHECK_TARGETS if board.is_check() else MIN_FORK_TARGETS
    return forks >= threshold
