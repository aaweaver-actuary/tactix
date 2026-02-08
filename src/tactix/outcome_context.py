"""Context objects for outcome evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tactix.config import Settings


class OutcomeResultEnum(StrEnum):
    """Possible outcome results."""

    SUCCESS = "success"
    MISSED = "missed"
    UNCLEAR = "unclear"
    FAILED_ATTEMPT = "failed_attempt"


@dataclass(frozen=True)
class BaseOutcomeContext:
    """Base outcome context for tactic evaluation."""

    result: OutcomeResultEnum
    motif: str
    best_move: str | None
    user_move_uci: str
    swing: int | None
    after_cp: int | None = None

    @property
    def was_missed(self) -> bool:
        """Return True if the outcome was missed."""
        return self.result == OutcomeResultEnum.MISSED

    @property
    def was_unclear(self) -> bool:
        """Return True if the mate was unclear."""
        return self.result == OutcomeResultEnum.UNCLEAR


@dataclass(frozen=True)
class OutcomeOverridesContext:
    """Context for applying outcome overrides."""

    outcome: BaseOutcomeContext
    best_motif: str | None
    after_cp: int
    mate_in_one: bool
    mate_in_two: bool
    settings: Settings | None


_VULTURE_USED = (
    OutcomeResultEnum.SUCCESS,
    OutcomeResultEnum.FAILED_ATTEMPT,
    BaseOutcomeContext.was_missed,
    BaseOutcomeContext.was_unclear,
)
