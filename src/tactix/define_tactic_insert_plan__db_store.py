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
    tactic_piece: object
    mate_type: object
    best_san: object
    explanation: object
    target_piece: object
    target_square: object
    eval_cp: object
