"""Decide when mate results should be upgraded."""

from tactix._is_missed_mate import _is_missed_mate
from tactix._is_unclear_two_move_mate import _is_unclear_two_move_mate
from tactix.analyze_tactics__positions import (
    _MATE_MISSED_SCORE_MULTIPLIER,
    MATE_IN_ONE,
    MATE_IN_TWO,
)
from tactix.outcome_context import BaseOutcomeContext


def _should_upgrade_mate_result(
    context: BaseOutcomeContext,
    mate_in: int | None,
) -> bool:
    """Return True when a mate result should be upgraded."""
    if mate_in not in {MATE_IN_ONE, MATE_IN_TWO}:
        return False
    missed_threshold = _MATE_MISSED_SCORE_MULTIPLIER * mate_in
    if context.after_cp is None:
        return False
    if _is_missed_mate(context.result, context.after_cp, missed_threshold):
        return True
    if mate_in == MATE_IN_TWO:
        return _is_unclear_two_move_mate(
            context.result,
            context.best_move,
            context.user_move_uci,
            context.swing,
        )
    return False
