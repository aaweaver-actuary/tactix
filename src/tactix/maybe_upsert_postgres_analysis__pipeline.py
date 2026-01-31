from __future__ import annotations

from tactix.pipeline_state__pipeline import logger
from tactix.postgres_store import upsert_analysis_tactic_with_outcome


def _maybe_upsert_postgres_analysis(
    pg_conn,
    analysis_pg_enabled: bool,
    tactic_row: dict[str, object],
    outcome_row: dict[str, object],
) -> bool:
    if pg_conn is None or not analysis_pg_enabled:
        return False
    try:
        upsert_analysis_tactic_with_outcome(
            pg_conn,
            tactic_row,
            outcome_row,
        )
    except Exception as exc:
        logger.warning("Postgres analysis upsert failed: %s", exc)
        return False
    else:
        return True
