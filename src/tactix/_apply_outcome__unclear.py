"""Apply unclear outcomes based on heuristic checks."""

from __future__ import annotations

# pylint: disable=redefined-outer-name
from collections.abc import Callable

from tactix.outcome_context import BaseOutcomeContext


def _apply_outcome__unclear(
    should_mark: Callable[[BaseOutcomeContext, int | None], bool],
    ctx: BaseOutcomeContext,
    threshold: int | None,
) -> str:
    if should_mark(ctx, threshold):
        return "unclear"
    return ctx.result
