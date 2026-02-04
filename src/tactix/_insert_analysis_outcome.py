"""Insert analysis outcome rows into Postgres."""

from tactix.ANALYSIS_SCHEMA import ANALYSIS_SCHEMA
from tactix.base_db_store import OutcomeInsertPlan


def _insert_analysis_outcome(
    cur,
    tactic_id: int,
    outcome_plan: OutcomeInsertPlan,
) -> None:
    """Insert an analysis outcome row for a tactic."""
    cur.execute(
        f"""
        INSERT INTO {ANALYSIS_SCHEMA}.tactic_outcomes (
            tactic_id,
            result,
            user_uci,
            eval_delta
        )
        VALUES (%s, %s, %s, %s)
        """,
        (
            tactic_id,
            outcome_plan.result,
            outcome_plan.user_uci,
            outcome_plan.eval_delta,
        ),
    )
