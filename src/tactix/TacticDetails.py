from dataclasses import dataclass


@dataclass(frozen=True)
class TacticDetails:
    motif: str
    severity: float
    best_move: str | None
    base_cp: int
    mate_in: int | None
    tactic_piece: str | None
    mate_type: str | None
    best_san: str | None
    explanation: str | None
