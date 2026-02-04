"""Shared helper for unclear mate outcomes."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from tactix._apply_outcome__unclear import _apply_outcome__unclear
from tactix.outcome_context import BaseOutcomeContext, MateOutcomeContext


def _build_mate_outcome(
    result: str,
    best_move: str | None,
    user_move_uci: str,
    after_cp: int,
) -> BaseOutcomeContext:
    return BaseOutcomeContext(
        result=result,
        motif="mate",
        best_move=best_move,
        user_move_uci=user_move_uci,
        swing=None,
        after_cp=after_cp,
    )


def _should_shift_mate_in_arg(
    context: MateOutcomeContext | str,
    mate_in: int | None,
    user_move_uci: str | None,
    after_cp: int | None,
    best_move: str | int | None,
) -> bool:
    return all(
        (
            isinstance(context, MateOutcomeContext),
            mate_in is None,
            user_move_uci is None,
            after_cp is None,
            isinstance(best_move, (int, type(None))),
        )
    )


def _resolve_mate_context(
    context: MateOutcomeContext | str,
    best_move: str | None,
    user_move_uci: str | None,
    after_cp: int | None,
) -> MateOutcomeContext:
    if isinstance(context, MateOutcomeContext):
        return context
    if user_move_uci is None or after_cp is None:
        raise TypeError("result, user_move_uci, and after_cp are required")
    outcome = _build_mate_outcome(context, best_move, user_move_uci, after_cp)
    return MateOutcomeContext(
        outcome=outcome,
        after_cp=after_cp,
        mate_in_one=False,
        mate_in_two=False,
    )


def _apply_outcome__unclear_mate(  # noqa: PLR0913
    should_mark: Callable[[BaseOutcomeContext, int | None], bool],
    context: MateOutcomeContext | str,
    best_move: str | None = None,
    user_move_uci: str | None = None,
    after_cp: int | None = None,
    mate_in: int | None = None,
) -> str:
    if _should_shift_mate_in_arg(context, mate_in, user_move_uci, after_cp, best_move):
        mate_in = cast(int | None, best_move)
        best_move = None
    resolved = _resolve_mate_context(context, best_move, user_move_uci, after_cp)
    return _apply_outcome__unclear(
        should_mark,
        resolved.outcome,
        mate_in,
    )
