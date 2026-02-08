"""Determine if a discovered-check outcome should be unclear."""

from tactix._is_swing_at_least import (
    _is_swing_at_least,
)
from tactix._is_unclear_discovered_check_candidate import _is_unclear_discovered_check_candidate
from tactix.outcome_context import BaseOutcomeContext


def _should_mark_unclear_discovered_check(
    context: BaseOutcomeContext,
    threshold: int | None,
) -> bool:
    if context.swing is None or threshold is None or context.best_move is None:
        return False
    if not _is_unclear_discovered_check_candidate(
        context.motif,
        context.best_move,
        context.user_move_uci,
        context.result,
    ):
        return False
    return _is_swing_at_least(context.swing, threshold)
