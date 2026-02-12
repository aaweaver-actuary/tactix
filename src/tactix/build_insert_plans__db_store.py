"""Build insert plans for tactic and outcome persistence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from tactix.define_outcome_insert_plan__db_store import OutcomeInsertPlan
from tactix.define_tactic_insert_plan__db_store import TacticInsertPlan


def require_position_id(
    tactic_row: Mapping[str, object],
    error_message: str,
) -> object:
    """Return the position id or raise a ValueError."""
    position_id = tactic_row.get("position_id")
    if position_id is None:
        raise ValueError(error_message)
    return position_id


def build_tactic_insert_plan(
    *,
    game_id: object,
    position_id: object,
    tactic_row: Mapping[str, object],
) -> TacticInsertPlan:
    """Build a tactic insert plan from a row mapping."""
    return TacticInsertPlan(
        game_id=game_id,
        position_id=position_id,
        motif=cast(str, tactic_row.get("motif", "unknown")),
        severity=tactic_row.get("severity", 0.0),
        best_uci=tactic_row.get("best_uci", ""),
        best_line_uci=tactic_row.get("best_line_uci"),
        tactic_piece=tactic_row.get("tactic_piece"),
        mate_type=tactic_row.get("mate_type"),
        best_san=tactic_row.get("best_san"),
        explanation=tactic_row.get("explanation"),
        target_piece=tactic_row.get("target_piece"),
        target_square=tactic_row.get("target_square"),
        eval_cp=tactic_row.get("eval_cp", 0),
        engine_depth=tactic_row.get("engine_depth"),
    )


def build_outcome_insert_plan(
    outcome_row: Mapping[str, object],
) -> OutcomeInsertPlan:
    """Build an outcome insert plan from a row mapping."""
    return OutcomeInsertPlan(
        result=cast(str, outcome_row.get("result", "unclear")),
        user_uci=outcome_row.get("user_uci", ""),
        eval_delta=outcome_row.get("eval_delta", 0),
    )
