from psycopg2.extensions import connection as PgConnection


def init_postgres_schema(conn: PgConnection) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tactix_ops")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tactix_ops.ops_events (
                id BIGSERIAL PRIMARY KEY,
                component TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT,
                profile TEXT,
                metadata JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ops_events_created_at_idx "
            "ON tactix_ops.ops_events (created_at DESC)"
        )
