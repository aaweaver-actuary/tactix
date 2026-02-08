"""Domain rules for practice attempt grading."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

FormatTacticExplanation = Callable[[str | None, str, str | None], tuple[str | None, str | None]]


@dataclass(frozen=True)
class PracticeAttemptInputs:
    """Grouped inputs for practice attempt payloads."""

    tactic: Mapping[str, object]
    tactic_id: int
    position_id: int
    attempted_uci: str
    best_uci: str
    correct: bool
    latency_ms: int | None


@dataclass(frozen=True)
class PracticeAttemptEvaluation:
    """Resolved payloads and metadata for a practice attempt."""

    attempt_payload: dict[str, object]
    best_san: str | None
    explanation: str | None
    message: str
    correct: bool
    best_uci: str
    attempted_uci: str


@dataclass(frozen=True)
class PracticeAttemptCandidate:
    """Inputs required to evaluate a practice attempt."""

    tactic: Mapping[str, object]
    tactic_id: int
    position_id: int
    attempted_uci: str
    latency_ms: int | None


def normalize_attempted_uci(attempted_uci: str) -> str:
    """Return a sanitized attempted UCI move."""
    trimmed = attempted_uci.strip()
    if not trimmed:
        raise ValueError("attempted_uci is required")
    return trimmed


def normalize_best_uci(tactic: Mapping[str, object]) -> str:
    """Return a normalized best UCI move from the tactic payload."""
    best_uci_raw = tactic.get("best_uci")
    return str(best_uci_raw).strip() if best_uci_raw is not None else ""


def is_attempt_correct(attempted_uci: str, best_uci: str) -> bool:
    """Return True when the attempt matches the best move."""
    return bool(best_uci) and attempted_uci.lower() == best_uci.lower()


def resolve_practice_explanation(
    tactic: Mapping[str, object],
    best_uci: str,
    format_tactic_explanation: FormatTacticExplanation,
) -> tuple[str | None, str | None]:
    """Resolve a tactic explanation from stored or generated data."""
    fen = _string_or_none(tactic.get("fen"))
    motif = _string_or_none(tactic.get("motif"))
    best_san = _string_or_none(tactic.get("best_san"))
    explanation = _string_or_none(tactic.get("explanation"))
    generated_san, generated_explanation = format_tactic_explanation(fen, best_uci, motif)
    return _resolve_explanation(best_san, explanation, generated_san, generated_explanation)


def build_practice_attempt_payload(inputs: PracticeAttemptInputs) -> dict[str, object]:
    """Return the payload used to record a practice attempt."""
    return {
        "tactic_id": inputs.tactic_id,
        "position_id": inputs.position_id,
        "source": inputs.tactic.get("source"),
        "attempted_uci": inputs.attempted_uci,
        "correct": inputs.correct,
        "success": inputs.correct,
        "best_uci": inputs.best_uci,
        "motif": inputs.tactic.get("motif", "unknown"),
        "severity": inputs.tactic.get("severity", 0.0),
        "eval_delta": inputs.tactic.get("eval_delta", 0) or 0,
        "latency_ms": inputs.latency_ms,
    }


def build_practice_message(
    correct: bool,
    tactic: Mapping[str, object],
    best_uci: str,
) -> str:
    """Return a user-facing message for the practice attempt."""
    if correct:
        return f"Correct! {tactic.get('motif', 'tactic')} found."
    return f"Missed it. Best move was {best_uci or '--'}."


def evaluate_practice_attempt(
    candidate: PracticeAttemptCandidate,
    format_tactic_explanation: FormatTacticExplanation,
) -> PracticeAttemptEvaluation:
    """Evaluate a practice attempt without persistence."""
    trimmed_attempt = normalize_attempted_uci(candidate.attempted_uci)
    best_uci = normalize_best_uci(candidate.tactic)
    correct = is_attempt_correct(trimmed_attempt, best_uci)
    best_san, explanation = resolve_practice_explanation(
        candidate.tactic,
        best_uci,
        format_tactic_explanation,
    )
    attempt_payload = build_practice_attempt_payload(
        PracticeAttemptInputs(
            tactic=candidate.tactic,
            tactic_id=candidate.tactic_id,
            position_id=candidate.position_id,
            attempted_uci=trimmed_attempt,
            best_uci=best_uci,
            correct=correct,
            latency_ms=candidate.latency_ms,
        )
    )
    message = build_practice_message(correct, candidate.tactic, best_uci)
    return PracticeAttemptEvaluation(
        attempt_payload=attempt_payload,
        best_san=best_san,
        explanation=explanation,
        message=message,
        correct=correct,
        best_uci=best_uci,
        attempted_uci=trimmed_attempt,
    )


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_explanation(
    best_san: str | None,
    explanation: str | None,
    generated_san: str | None,
    generated_explanation: str | None,
) -> tuple[str | None, str | None]:
    if not best_san:
        best_san = generated_san or None
    if not explanation:
        explanation = generated_explanation or None
    return best_san, explanation
