"""Fetch recent analysis tactics from Postgres."""

from typing import Any

from psycopg2.extras import RealDictCursor

from tactix.ANALYSIS_SCHEMA import ANALYSIS_SCHEMA
from tactix.config import Settings
from tactix.init_analysis_schema import init_analysis_schema
from tactix.postgres_analysis_enabled import postgres_analysis_enabled
from tactix.postgres_connection import postgres_connection


def fetch_analysis_tactics(settings: Settings, limit: int = 10) -> list[dict[str, Any]]:
    """Return recent tactics for the given settings."""
    with postgres_connection(settings) as conn:
        if conn is None or not postgres_analysis_enabled(settings):
            return []
        init_analysis_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT
                    t.tactic_id,
                    t.game_id,
                    t.position_id,
                    t.motif,
                    t.severity,
                    t.best_uci,
                    t.best_san,
                    t.explanation,
                    t.eval_cp,
                    t.created_at,
                    o.result,
                    o.user_uci,
                    o.eval_delta,
                    o.created_at AS outcome_created_at
                FROM {ANALYSIS_SCHEMA}.tactics t
                LEFT JOIN {ANALYSIS_SCHEMA}.tactic_outcomes o
                    ON o.tactic_id = t.tactic_id
                ORDER BY t.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]
