"""Shared helper for unclear mate outcomes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from tactix._apply_outcome__unclear import _apply_outcome__unclear
from tactix.outcome_context import BaseOutcomeContext, MateOutcomeContext


@dataclass(frozen=True)
class MateOutcomeArgs:
    """Arguments for unclear mate outcome handling."""

    best_move: str | int | None = None
    user_move_uci: str | None = None
    after_cp: int | None = None
    mate_in: int | None = None


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
    args: MateOutcomeArgs,
) -> bool:
    return all(
        (
            isinstance(context, MateOutcomeContext),
            args.mate_in is None,
            args.user_move_uci is None,
            args.after_cp is None,
            isinstance(args.best_move, (int, type(None))),
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


def _apply_outcome__unclear_mate(
    should_mark: Callable[[BaseOutcomeContext, int | None], bool],
    context: MateOutcomeContext | str,
    args: MateOutcomeArgs | None = None,
) -> str:
    if args is None:
        args = MateOutcomeArgs()
    best_move = args.best_move
    mate_in = args.mate_in
    if _should_shift_mate_in_arg(context, args):
        mate_in = cast(int | None, best_move)
        best_move = None
    resolved = _resolve_mate_context(
        context,
        cast(str | None, best_move),
        args.user_move_uci,
        args.after_cp,
    )
    return _apply_outcome__unclear(
        should_mark,
        resolved.outcome,
        mate_in,
    )


def _build_mate_outcome_args(
    best_move: str | None,
    user_move_uci: str | None,
    after_cp: int | None,
    mate_in: int | None,
) -> MateOutcomeArgs:
    return MateOutcomeArgs(
        best_move=best_move,
        user_move_uci=user_move_uci,
        after_cp=after_cp,
        mate_in=mate_in,
    )
