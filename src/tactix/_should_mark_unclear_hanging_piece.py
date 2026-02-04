"""Determine if a hanging piece outcome should be unclear."""

from typing import cast

from tactix._compute_eval__failed_attempt_threshold import (
    _compute_eval__failed_attempt_threshold,
)
from tactix._is_swing_at_least import _is_swing_at_least
from tactix._is_unclear_hanging_piece_candidate import _is_unclear_hanging_piece_candidate
from tactix.outcome_context import BaseOutcomeContext


def _should_mark_unclear_hanging_piece(
    context: BaseOutcomeContext,
    threshold: int | None,
) -> bool:
    """Return True when a hanging piece result is unclear."""
    if not _has_unclear_hanging_piece_inputs(context, threshold):
        return False
    best_move = cast(str, context.best_move)
    swing = cast(int, context.swing)
    threshold_value = cast(int, threshold)
    if not _is_unclear_hanging_piece_candidate(
        context.motif,
        best_move,
        context.user_move_uci,
        context.result,
    ):
        return False
    if _fails_hanging_piece_failed_attempt(context):
        return False
    return _is_swing_at_least(swing, threshold_value)


def _has_unclear_hanging_piece_inputs(
    context: BaseOutcomeContext,
    threshold: int | None,
) -> bool:
    return all(
        (
            context.swing is not None,
            threshold is not None,
            context.best_move is not None,
        )
    )


def _fails_hanging_piece_failed_attempt(context: BaseOutcomeContext) -> bool:
    if context.result != "failed_attempt" or context.swing is None:
        return False
    failed_attempt_threshold = _compute_eval__failed_attempt_threshold(
        "hanging_piece",
        None,
    )
    return failed_attempt_threshold is not None and context.swing <= failed_attempt_threshold
