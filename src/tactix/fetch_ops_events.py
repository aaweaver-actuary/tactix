from typing import Any

from psycopg2.extras import RealDictCursor

from tactix.config import Settings
from tactix.init_postgres_schema import init_postgres_schema
from tactix.postgres_connection import postgres_connection


def fetch_ops_events(settings: Settings, limit: int = 10) -> list[dict[str, Any]]:
    with postgres_connection(settings) as conn:
        if conn is None:
            return []
        init_postgres_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, component, event_type, source, profile, metadata, created_at
                FROM tactix_ops.ops_events
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]
