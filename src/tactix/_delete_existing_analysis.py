"""Delete existing analysis rows for a position."""

from tactix.ANALYSIS_SCHEMA import ANALYSIS_SCHEMA


def _delete_existing_analysis(cur, position_id: int) -> None:
    """Delete existing tactics and outcomes for a position id."""
    cur.execute(
        f"""
        DELETE FROM {ANALYSIS_SCHEMA}.tactic_outcomes
        WHERE tactic_id IN (
            SELECT tactic_id FROM {ANALYSIS_SCHEMA}.tactics WHERE position_id = %s
        )
        """,
        (position_id,),
    )
    cur.execute(
        f"DELETE FROM {ANALYSIS_SCHEMA}.tactics WHERE position_id = %s",
        (position_id,),
    )
