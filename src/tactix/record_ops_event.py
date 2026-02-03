from typing import Any

from psycopg2.extras import Json

from tactix.config import Settings
from tactix.init_postgres_schema import init_postgres_schema
from tactix.postgres_connection import postgres_connection


def record_ops_event(
    settings: Settings,
    component: str,
    event_type: str,
    source: str | None = None,
    profile: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    with postgres_connection(settings) as conn:
        if conn is None:
            return False
        init_postgres_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tactix_ops.ops_events
                    (component, event_type, source, profile, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    component,
                    event_type,
                    source,
                    profile,
                    Json(metadata or {}),
                ),
            )
        return True
