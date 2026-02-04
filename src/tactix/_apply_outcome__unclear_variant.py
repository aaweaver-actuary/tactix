"""Shared helper for unclear outcome variants."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from tactix._apply_outcome__unclear import _apply_outcome__unclear
from tactix.outcome_context import BaseOutcomeContext
from tactix.resolve_unclear_outcome_context import resolve_unclear_outcome_context
from tactix.unclear_outcome_params import UnclearOutcomeParams


def _apply_outcome__unclear_variant(
    should_mark: Callable[[BaseOutcomeContext, int | None], bool],
    context: BaseOutcomeContext | str,
    *args: object,
    **kwargs: object,
) -> str:
    threshold = kwargs.get("threshold")
    if isinstance(context, BaseOutcomeContext) and args:
        if threshold is None:
            threshold = args[0]
        args = ()
    legacy = {
        "motif": kwargs.get("motif"),
        "best_move": kwargs.get("best_move"),
        "user_move_uci": kwargs.get("user_move_uci"),
        "swing": kwargs.get("swing"),
    }
    resolved, resolved_threshold = resolve_unclear_outcome_context(
        context,
        cast(int | str | None, threshold),
        args,
        cast(UnclearOutcomeParams | None, kwargs.get("params")),
        legacy,
    )
    return _apply_outcome__unclear(should_mark, resolved, resolved_threshold)
