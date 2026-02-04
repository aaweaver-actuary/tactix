"""Insert analysis tactic rows into Postgres."""

from tactix.ANALYSIS_SCHEMA import ANALYSIS_SCHEMA
from tactix.base_db_store import TacticInsertPlan


def _insert_analysis_tactic(cur, tactic_plan: TacticInsertPlan) -> int:
    """Insert a tactic row and return its id."""
    cur.execute(
        f"""
        INSERT INTO {ANALYSIS_SCHEMA}.tactics (
            game_id,
            position_id,
            motif,
            severity,
            best_uci,
            best_san,
            explanation,
            eval_cp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING tactic_id
        """,
        (
            tactic_plan.game_id,
            tactic_plan.position_id,
            tactic_plan.motif,
            tactic_plan.severity,
            tactic_plan.best_uci,
            tactic_plan.best_san,
            tactic_plan.explanation,
            tactic_plan.eval_cp,
        ),
    )
    tactic_id_row = cur.fetchone()
    return int(tactic_id_row[0]) if tactic_id_row else 0
