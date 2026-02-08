from dataclasses import dataclass

from tactix.OutcomeDetails import OutcomeDetails
from tactix.TacticDetails import TacticDetails


@dataclass(frozen=True)
class TacticRowInput:
    position: dict[str, object]
    details: TacticDetails
    outcome: OutcomeDetails
