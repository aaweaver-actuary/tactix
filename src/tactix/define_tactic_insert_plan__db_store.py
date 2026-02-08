"""Define the tactic insert plan for persistence."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TacticInsertPlan:  # pylint: disable=too-many-instance-attributes
    """Payload for inserting a tactic row."""

    game_id: object
    position_id: object
    motif: str
    severity: object
    best_uci: object
    best_san: object
    explanation: object
    eval_cp: object
