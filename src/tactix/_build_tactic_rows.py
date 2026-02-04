from dataclasses import dataclass

from tactix.utils.logger import funclogger


@dataclass(frozen=True)
class TacticRowInput:
    position: dict[str, object]
    motif: str
    severity: float
    best_move: str | None
    base_cp: int
    mate_in: int | None
    best_san: str | None
    explanation: str | None
    result: str
    user_move_uci: str
    delta: int


@funclogger
def _build_tactic_rows(
    inputs: TacticRowInput,
) -> tuple[dict[str, object], dict[str, object]]:
    tactic_row: dict[str, object] = {
        "game_id": inputs.position["game_id"],
        "position_id": inputs.position.get("position_id"),
        "motif": inputs.motif,
        "severity": inputs.severity,
        "best_uci": inputs.best_move or "",
        "eval_cp": inputs.base_cp,
        "best_san": inputs.best_san,
        "explanation": inputs.explanation,
        "mate_in": inputs.mate_in,
    }
    outcome_row: dict[str, object] = {
        "tactic_id": None,  # filled by caller
        "result": inputs.result,
        "user_uci": inputs.user_move_uci,
        "eval_delta": inputs.delta,
    }
    return tactic_row, outcome_row
