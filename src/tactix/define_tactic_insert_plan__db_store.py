from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TacticInsertPlan:
    game_id: object
    position_id: object
    motif: str
    severity: object
    best_uci: object
    best_san: object
    explanation: object
    eval_cp: object
