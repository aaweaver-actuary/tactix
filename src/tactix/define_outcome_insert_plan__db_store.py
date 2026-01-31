from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class OutcomeInsertPlan:
    result: str
    user_uci: object
    eval_delta: object
