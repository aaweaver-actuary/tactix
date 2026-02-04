"""Apply unclear mate-in-two outcomes."""

from tactix._apply_outcome__unclear_mate import (
    _apply_outcome__unclear_mate,
    _build_mate_outcome_args,
)
from tactix._should_mark_unclear_mate_in_two import _should_mark_unclear_mate_in_two
from tactix.outcome_context import MateOutcomeContext


def _apply_outcome__unclear_mate_in_two(
    context: MateOutcomeContext | str,
    best_move: str | None = None,
    user_move_uci: str | None = None,
    after_cp: int | None = None,
    mate_in: int | None = None,
) -> str:
    return _apply_outcome__unclear_mate(
        _should_mark_unclear_mate_in_two,
        context,
        args=_build_mate_outcome_args(best_move, user_move_uci, after_cp, mate_in),
    )
