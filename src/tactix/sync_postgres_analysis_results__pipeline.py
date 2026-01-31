from __future__ import annotations

from tactix.config import Settings
from tactix.db.duckdb_store import fetch_recent_tactics
from tactix.define_pipeline_state__pipeline import DEFAULT_SYNC_LIMIT, logger


def _sync_postgres_analysis_results(
    conn,
    pg_conn,
    settings: Settings,
    limit: int = DEFAULT_SYNC_LIMIT,
) -> int:
    if pg_conn is None:
        return 0
    synced = 0
    recent = fetch_recent_tactics(conn, limit=limit, source=settings.source)
    for row in recent:
        tactic_row = {
            "game_id": row.get("game_id"),
            "position_id": row.get("position_id"),
            "motif": row.get("motif", "unknown"),
            "severity": row.get("severity", 0.0),
            "best_uci": row.get("best_uci", ""),
            "best_san": row.get("best_san"),
            "explanation": row.get("explanation"),
            "eval_cp": row.get("eval_cp", 0),
        }
        outcome_row = {
            "result": row.get("result", "unclear"),
            "user_uci": row.get("user_uci", ""),
            "eval_delta": row.get("eval_delta", 0),
        }
        try:
            from tactix import pipeline as pipeline_module  # noqa: PLC0415

            pipeline_module.upsert_analysis_tactic_with_outcome(
                pg_conn,
                tactic_row,
                outcome_row,
            )
            synced += 1
        except Exception as exc:
            logger.warning("Postgres analysis sync failed: %s", exc)
    return synced
