"""Shared SQL fragments for tactics queries and inserts."""

TACTIC_COLUMNS = """
    t.tactic_id,
    t.game_id,
    t.position_id,
    t.motif,
    t.severity,
    t.best_uci,
    t.best_san,
    t.explanation,
    t.eval_cp
"""

TACTIC_ANALYSIS_COLUMNS = """
    t.tactic_id,
    t.position_id,
    t.game_id,
    t.motif,
    t.severity,
    t.best_uci,
    t.best_san,
    t.explanation,
    t.eval_cp,
    t.created_at
"""

OUTCOME_COLUMNS = """
    o.result,
    o.user_uci,
    o.eval_delta
"""

TACTIC_QUEUE_COLUMNS = """
    t.tactic_id,
    t.game_id,
    t.position_id,
    t.motif,
    t.severity,
    t.best_uci,
    t.eval_cp,
    t.created_at
"""

TACTIC_INSERT_COLUMNS: tuple[str, ...] = (
    "game_id",
    "position_id",
    "motif",
    "severity",
    "best_uci",
    "best_san",
    "explanation",
    "eval_cp",
)


_VULTURE_USED = (TACTIC_INSERT_COLUMNS,)
