"""Define the outcome insert plan for persistence."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class OutcomeInsertPlan:
    """Payload for inserting an outcome row."""

    result: str
    user_uci: object
    eval_delta: object
