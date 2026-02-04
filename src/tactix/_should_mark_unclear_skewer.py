"""Determine if a skewer outcome should be marked unclear."""

from tactix._is_swing_at_least import _is_swing_at_least
from tactix._is_unclear_skewer_candidate import _is_unclear_skewer_candidate
from tactix.outcome_context import BaseOutcomeContext


def _should_mark_unclear_skewer(
    context: BaseOutcomeContext,
    threshold: int | None,
) -> bool:
    """Return True when a skewer result is unclear."""
    if context.swing is None or threshold is None or context.best_move is None:
        return False
    if not _is_unclear_skewer_candidate(
        context.motif,
        context.best_move,
        context.user_move_uci,
        context.result,
    ):
        return False
    return _is_swing_at_least(context.swing, threshold)
