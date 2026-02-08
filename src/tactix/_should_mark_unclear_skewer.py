"""Determine if a skewer outcome should be marked unclear."""

from tactix._is_unclear_skewer_candidate import _is_unclear_skewer_candidate
from tactix._should_mark_unclear_candidate import _should_mark_unclear_candidate
from tactix.outcome_context import BaseOutcomeContext
from tactix.utils.logger import funclogger


@funclogger
def _should_mark_unclear_skewer(
    context: BaseOutcomeContext,
    threshold: int | None,
) -> bool:
    """Return True when a skewer result is unclear."""
    return _should_mark_unclear_candidate(
        context,
        threshold,
        _is_unclear_skewer_candidate,
    )
