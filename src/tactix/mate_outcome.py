from dataclasses import dataclass

from tactix._should_upgrade_mate_result import _should_upgrade_mate_result
from tactix.analyze_tactics__positions import MATE_IN_ONE, MATE_IN_TWO
from tactix.outcome_context import BaseOutcomeContext


@dataclass(frozen=True)
class MateOutcome:
    """Context for mate outcome evaluation."""

    outcome: BaseOutcomeContext
    after_cp: int
    mate_in_one: bool
    mate_in_two: bool

    @property
    def mate_in(self) -> int | None:
        if self.mate_in_one:
            return MATE_IN_ONE
        if self.mate_in_two:
            return MATE_IN_TWO
        return None

    @property
    def should_be_upgraded(self) -> bool:
        """Return True if the mate outcome should be upgraded."""
        return _should_upgrade_mate_result(self.outcome, self.mate_in)
