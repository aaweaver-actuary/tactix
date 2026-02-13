"""Shared SQL fragments for tactics queries and inserts."""

TACTIC_COLUMNS = """
    t.tactic_id,
    t.game_id,
    t.position_id,
    t.motif,
    t.severity,
    t.best_uci,
    t.best_line_uci,
    t.tactic_piece,
    t.mate_type,
    t.best_san,
    t.explanation,
    t.target_piece,
    t.target_square,
    t.eval_cp,
    t.engine_depth,
    t.confidence
"""

TACTIC_ANALYSIS_COLUMNS = """
    t.tactic_id,
    t.position_id,
    t.game_id,
    t.motif,
    t.severity,
    t.best_uci,
    t.best_line_uci,
    t.tactic_piece,
    t.mate_type,
    t.best_san,
    t.explanation,
    t.target_piece,
    t.target_square,
    t.eval_cp,
    t.engine_depth,
    t.confidence,
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
    t.best_line_uci,
    t.tactic_piece,
    t.mate_type,
    t.eval_cp,
    t.target_piece,
    t.target_square,
    t.engine_depth,
    t.confidence,
    t.created_at
"""

TACTIC_INSERT_COLUMNS: tuple[str, ...] = (
    "game_id",
    "position_id",
    "motif",
    "severity",
    "best_uci",
    "best_line_uci",
    "tactic_piece",
    "mate_type",
    "best_san",
    "explanation",
    "target_piece",
    "target_square",
    "eval_cp",
    "engine_depth",
    "confidence",
)


_VULTURE_USED = (TACTIC_INSERT_COLUMNS,)
