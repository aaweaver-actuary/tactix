from dataclasses import replace

from tactix._apply_outcome__unclear_mate_in_one import _apply_outcome__unclear_mate_in_one
from tactix._apply_outcome__unclear_mate_in_two import (
    _apply_outcome__unclear_mate_in_two,
)
from tactix._override_mate_motif import _override_mate_motif
from tactix._resolve_mate_in import _resolve_mate_in
from tactix._should_upgrade_mate_result import _should_upgrade_mate_result
from tactix.outcome_context import MateOutcomeContext


def _apply_mate_overrides(
    ctx: MateOutcomeContext,
) -> tuple[str, str, int | None]:
    mate_in = _resolve_mate_in(ctx.mate_in_one, ctx.mate_in_two)
    motif = _override_mate_motif(ctx.outcome.motif, mate_in)
    result = _apply_outcome__unclear_mate_in_one(ctx, mate_in=mate_in)
    updated_context = replace(ctx.outcome, result=result)
    result = _apply_outcome__unclear_mate_in_two(
        replace(ctx, outcome=updated_context),
        mate_in=mate_in,
    )
    if _should_upgrade_mate_result(updated_context, mate_in):
        result = "failed_attempt"
    return result, motif, mate_in
