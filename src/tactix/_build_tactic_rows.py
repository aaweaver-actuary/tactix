from tactix.utils.logger import funclogger


@funclogger
def _build_tactic_rows(
    position: dict[str, object],
    motif: str,
    severity: float,
    best_move: str | None,
    base_cp: int,
    mate_in: int | None,
    best_san: str | None,
    explanation: str | None,
    result: str,
    user_move_uci: str,
    delta: int,
) -> tuple[dict[str, object], dict[str, object]]:
    tactic_row = {
        "game_id": position["game_id"],
        "position_id": position.get("position_id"),
        "motif": motif,
        "severity": severity,
        "best_uci": best_move or "",
        "eval_cp": base_cp,
        "best_san": best_san,
        "explanation": explanation,
        "mate_in": mate_in,
    }
    outcome_row = {
        "tactic_id": None,  # filled by caller
        "result": result,
        "user_uci": user_move_uci,
        "eval_delta": delta,
    }
    return tactic_row, outcome_row
