from __future__ import annotations

from dataclasses import dataclass

from tactix.TacticRowInput import TacticRowInput
from tactix.utils.logger import funclogger


@dataclass(frozen=True)
class TacticRowDetails:
    best_uci: str | None
    best_san: str | None
    explanation: str | None
    mate_in: int | None


@dataclass(frozen=True)
class TacticRow:
    game_id: str
    position_id: str | None
    motif: str
    severity: float
    eval_cp: int
    details: TacticRowDetails

    @classmethod
    @funclogger
    def from_inputs(cls, inputs: TacticRowInput) -> TacticRow:
        return cls(
            game_id=inputs.position["game_id"],
            position_id=inputs.position.get("position_id"),
            motif=inputs.details.motif,
            severity=inputs.details.severity,
            eval_cp=inputs.details.base_cp,
            details=TacticRowDetails(
                best_uci=inputs.details.best_move,
                best_san=inputs.details.best_san,
                explanation=inputs.details.explanation,
                mate_in=inputs.details.mate_in,
            ),
        )

    def to_row(self) -> dict[str, object]:
        return {
            "game_id": self.game_id,
            "position_id": self.position_id,
            "motif": self.motif,
            "severity": self.severity,
            "best_uci": self.details.best_uci,
            "eval_cp": self.eval_cp,
            "best_san": self.details.best_san,
            "explanation": self.details.explanation,
            "mate_in": self.details.mate_in,
        }
