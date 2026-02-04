"""Context objects for outcome evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from tactix.config import Settings


@dataclass(frozen=True)
class BaseOutcomeContext:
    """Base outcome context for tactic evaluation."""

    result: str
    motif: str
    best_move: str | None
    user_move_uci: str
    swing: int | None
    after_cp: int | None = None


@dataclass(frozen=True)
class MateOutcomeContext:
    """Context for mate outcome evaluation."""

    outcome: BaseOutcomeContext
    after_cp: int
    mate_in_one: bool
    mate_in_two: bool


@dataclass(frozen=True)
class OutcomeOverridesContext:
    """Context for applying outcome overrides."""

    outcome: BaseOutcomeContext
    best_motif: str | None
    after_cp: int
    mate_in_one: bool
    mate_in_two: bool
    settings: Settings | None
