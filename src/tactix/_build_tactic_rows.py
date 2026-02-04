from dataclasses import dataclass

from tactix.utils.logger import funclogger


@dataclass(frozen=True)
class TacticDetails:
    motif: str
    severity: float
    best_move: str | None
    base_cp: int
    mate_in: int | None
    best_san: str | None
    explanation: str | None


@dataclass(frozen=True)
class OutcomeDetails:
    result: str
    user_move_uci: str
    delta: int


@dataclass(frozen=True)
class TacticRowInput:
    position: dict[str, object]
    details: TacticDetails
    outcome: OutcomeDetails


@funclogger
def _build_tactic_rows(
    inputs: TacticRowInput,
) -> tuple[dict[str, object], dict[str, object]]:
    tactic_row: dict[str, object] = {
        "game_id": inputs.position["game_id"],
        "position_id": inputs.position.get("position_id"),
        "motif": inputs.details.motif,
        "severity": inputs.details.severity,
        "best_uci": inputs.details.best_move or "",
        "eval_cp": inputs.details.base_cp,
        "best_san": inputs.details.best_san,
        "explanation": inputs.details.explanation,
        "mate_in": inputs.details.mate_in,
    }
    outcome_row: dict[str, object] = {
        "tactic_id": None,  # filled by caller
        "result": inputs.outcome.result,
        "user_uci": inputs.outcome.user_move_uci,
        "eval_delta": inputs.outcome.delta,
    }
    return tactic_row, outcome_row
