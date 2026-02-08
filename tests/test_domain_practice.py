import pytest

from tactix.domain.practice import (
    PracticeAttemptCandidate,
    build_practice_message,
    evaluate_practice_attempt,
    normalize_attempted_uci,
)


def test_normalize_attempted_uci_requires_value() -> None:
    with pytest.raises(ValueError):
        normalize_attempted_uci("   ")


def test_evaluate_practice_attempt_prefers_stored_explanation() -> None:
    def fake_format(fen: str | None, best_uci: str, motif: str | None) -> tuple[str | None, str | None]:
        return "e4", "generated"

    tactic = {
        "source": "lichess",
        "motif": "pin",
        "best_uci": "e2e4",
        "best_san": "e4",
        "explanation": "stored",
    }
    evaluation = evaluate_practice_attempt(
        PracticeAttemptCandidate(
            tactic=tactic,
            tactic_id=10,
            position_id=20,
            attempted_uci="e2e4",
            latency_ms=None,
        ),
        fake_format,
    )
    assert evaluation.correct is True
    assert evaluation.best_san == "e4"
    assert evaluation.explanation == "stored"
    assert evaluation.attempt_payload["attempted_uci"] == "e2e4"


def test_evaluate_practice_attempt_falls_back_to_generated_explanation() -> None:
    def fake_format(fen: str | None, best_uci: str, motif: str | None) -> tuple[str | None, str | None]:
        return "Qh5#", "mate tactic"

    tactic = {
        "source": "lichess",
        "motif": "mate",
        "best_uci": "d1h5",
    }
    evaluation = evaluate_practice_attempt(
        PracticeAttemptCandidate(
            tactic=tactic,
            tactic_id=11,
            position_id=21,
            attempted_uci="d1h5",
            latency_ms=120,
        ),
        fake_format,
    )
    assert evaluation.best_san == "Qh5#"
    assert evaluation.explanation == "mate tactic"
    assert evaluation.attempt_payload["latency_ms"] == 120


def test_build_practice_message() -> None:
    tactic = {"motif": "fork"}
    assert build_practice_message(True, tactic, "e2e4") == "Correct! fork found."
    assert build_practice_message(False, tactic, "e2e4") == "Missed it. Best move was e2e4."
