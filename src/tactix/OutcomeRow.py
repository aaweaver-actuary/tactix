from __future__ import annotations

from dataclasses import dataclass

from tactix.TacticRowInput import TacticRowInput
from tactix.utils.logger import funclogger


@dataclass
class OutcomeRow:
    tactic_id: int | None
    result: str
    user_uci: str
    eval_delta: int

    @classmethod
    @funclogger
    def from_inputs(cls, inputs: TacticRowInput) -> OutcomeRow:
        return cls(
            tactic_id=None,  # filled by caller
            result=inputs.outcome.result,
            user_uci=inputs.outcome.user_move_uci,
            eval_delta=inputs.outcome.delta,
        )
