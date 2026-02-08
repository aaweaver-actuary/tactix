from tactix.domain.tactics_outcome import (
    resolve_unclear_outcome_context,
    should_override_failed_attempt,
)
from tactix.outcome_context import BaseOutcomeContext


def test_should_override_failed_attempt() -> None:
    assert should_override_failed_attempt("unclear", -150, -100, "fork")
    assert not should_override_failed_attempt("missed", -150, -100, "fork")


def test_resolve_unclear_outcome_context_from_string() -> None:
    resolved, resolved_threshold = resolve_unclear_outcome_context(
        "unclear",
        120,
        ("fork", "e2e4", "e2e3", -90),
        None,
        {},
    )
    assert isinstance(resolved, BaseOutcomeContext)
    assert resolved.result == "unclear"
    assert resolved.motif == "fork"
    assert resolved.best_move == "e2e4"
    assert resolved.user_move_uci == "e2e3"
    assert resolved.swing == -90
    assert resolved_threshold == 120


def test_resolve_unclear_outcome_context_full_args() -> None:
    resolved, resolved_threshold = resolve_unclear_outcome_context(
        "unclear",
        None,
        ("fork", "e2e4", "e2e3", -90, 140),
        None,
        {},
    )
    assert isinstance(resolved, BaseOutcomeContext)
    assert resolved.result == "unclear"
    assert resolved.motif == "fork"
    assert resolved.best_move == "e2e4"
    assert resolved.user_move_uci == "e2e3"
    assert resolved.swing == -90
    assert resolved_threshold == 140
