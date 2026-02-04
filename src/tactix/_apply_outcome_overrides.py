"""Apply outcome overrides based on eval thresholds."""

from dataclasses import replace

from tactix._apply_mate_overrides import _apply_mate_overrides
from tactix._apply_outcome__failed_attempt_hanging_piece import (
    _apply_outcome__failed_attempt_hanging_piece,
)
from tactix._apply_outcome__failed_attempt_line_tactics import (
    _apply_outcome__failed_attempt_line_tactics,
)
from tactix._apply_outcome__unclear_discovered_attack import (
    _apply_outcome__unclear_discovered_attack,
)
from tactix._apply_outcome__unclear_discovered_check import _apply_outcome__unclear_discovered_check
from tactix._apply_outcome__unclear_fork import _apply_outcome__unclear_fork
from tactix._apply_outcome__unclear_hanging_piece import _apply_outcome__unclear_hanging_piece
from tactix._apply_outcome__unclear_pin import _apply_outcome__unclear_pin
from tactix._apply_outcome__unclear_skewer import _apply_outcome__unclear_skewer
from tactix._compute_eval__discovered_attack_unclear_threshold import (
    _compute_eval__discovered_attack_unclear_threshold,
)
from tactix._compute_eval__discovered_check_unclear_threshold import (
    _compute_eval__discovered_check_unclear_threshold,
)
from tactix._compute_eval__failed_attempt_threshold import (
    _compute_eval__failed_attempt_threshold,
)
from tactix._compute_eval__fork_unclear_threshold import _compute_eval__fork_unclear_threshold
from tactix._compute_eval__hanging_piece_unclear_threshold import (
    _compute_eval__hanging_piece_unclear_threshold,
)
from tactix._compute_eval__pin_unclear_threshold import _compute_eval__pin_unclear_threshold
from tactix._compute_eval__skewer_unclear_threshold import _compute_eval__skewer_unclear_threshold
from tactix.outcome_context import MateOutcomeContext, OutcomeOverridesContext


def _apply_outcome_overrides(
    ctx: OutcomeOverridesContext,
) -> tuple[str, str, int | None]:
    """Apply override rules and return updated result and motif."""
    outcome = ctx.outcome
    result, motif = _apply_outcome__failed_attempt_line_tactics(
        outcome.result,
        outcome.motif,
        ctx.best_motif,
        outcome.swing,
        ctx.settings,
    )
    outcome = replace(outcome, result=result, motif=motif)
    result = _apply_outcome__unclear_fork(
        outcome,
        _compute_eval__fork_unclear_threshold(ctx.settings),
    )
    outcome = replace(outcome, result=result)
    result = _apply_outcome__unclear_skewer(
        outcome,
        _compute_eval__skewer_unclear_threshold(ctx.settings),
    )
    outcome = replace(outcome, result=result)
    result = _apply_outcome__unclear_discovered_attack(
        outcome,
        _compute_eval__discovered_attack_unclear_threshold(ctx.settings),
    )
    outcome = replace(outcome, result=result)
    result = _apply_outcome__unclear_discovered_check(
        outcome,
        _compute_eval__discovered_check_unclear_threshold(ctx.settings),
    )
    outcome = replace(outcome, result=result)
    result = _apply_outcome__unclear_hanging_piece(
        outcome,
        _compute_eval__hanging_piece_unclear_threshold(ctx.settings),
    )
    result, motif = _apply_outcome__failed_attempt_hanging_piece(
        result,
        outcome.motif,
        ctx.best_motif,
        outcome.swing,
        _compute_eval__failed_attempt_threshold("hanging_piece", ctx.settings),
    )
    outcome = replace(outcome, result=result, motif=motif)
    result = _apply_outcome__unclear_pin(
        outcome,
        _compute_eval__pin_unclear_threshold(ctx.settings),
    )
    outcome = replace(outcome, result=result)
    mate_context = MateOutcomeContext(
        outcome=outcome,
        after_cp=ctx.after_cp,
        mate_in_one=ctx.mate_in_one,
        mate_in_two=ctx.mate_in_two,
    )
    return _apply_mate_overrides(mate_context)
