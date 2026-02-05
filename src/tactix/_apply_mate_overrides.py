from dataclasses import replace

from tactix._apply_outcome__unclear_mate_in_one import _apply_outcome__unclear_mate_in_one
from tactix._apply_outcome__unclear_mate_in_two import (
    _apply_outcome__unclear_mate_in_two,
)
from tactix._override_mate_motif import _override_mate_motif
from tactix.mate_outcome import MateOutcome

MateOverrideResult = tuple[str, str, int | None]


def _apply_mate_overrides(ctx: MateOutcome) -> MateOverrideResult:
    mate_in = ctx.mate_in
    motif = _override_mate_motif(ctx.outcome.motif, mate_in)
    result = _apply_outcome__unclear_mate_in_one(ctx, mate_in=mate_in)
    updated_context = replace(ctx.outcome, result=result)
    result = _apply_outcome__unclear_mate_in_two(
        replace(ctx, outcome=updated_context),
        mate_in=mate_in,
    )
    if ctx.should_be_upgraded:
        result = "failed_attempt"
    return result, motif, mate_in
