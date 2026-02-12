from dataclasses import dataclass


@dataclass(frozen=True)
class TacticDetails:  # pylint: disable=too-many-instance-attributes
    motif: str
    severity: float
    best_move: str | None
    best_line_uci: str | None
    base_cp: int
    engine_depth: int | None
    mate_in: int | None
    tactic_piece: str | None
    mate_type: str | None
    best_san: str | None
    explanation: str | None
    target_piece: str | None
    target_square: str | None
