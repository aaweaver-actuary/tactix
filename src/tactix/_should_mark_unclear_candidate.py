"""Shared helper for unclear outcome detection."""

from __future__ import annotations

from collections.abc import Callable

from tactix._is_swing_at_least import _is_swing_at_least
from tactix.outcome_context import BaseOutcomeContext


def _should_mark_unclear_candidate(
    context: BaseOutcomeContext,
    threshold: int | None,
    predicate: Callable[[str, str, str, str], bool],
) -> bool:
    """Return True when an outcome should be marked unclear."""
    if context.swing is None or threshold is None or context.best_move is None:
        return False
    if not predicate(
        context.motif,
        context.best_move,
        context.user_move_uci,
        context.result,
    ):
        return False
    return _is_swing_at_least(context.swing, threshold)
