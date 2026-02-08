"""Initialize Postgres ops schema."""

from psycopg2.extensions import connection as PgConnection  # noqa: N812


def init_postgres_schema(conn: PgConnection) -> None:
    """Ensure the ops_events table exists."""
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
                run_id TEXT,
                op_id TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute("ALTER TABLE tactix_ops.ops_events ADD COLUMN IF NOT EXISTS run_id TEXT")
        cur.execute("ALTER TABLE tactix_ops.ops_events ADD COLUMN IF NOT EXISTS op_id TEXT")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ops_events_created_at_idx "
            "ON tactix_ops.ops_events (created_at DESC)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ops_events_run_id_idx ON tactix_ops.ops_events (run_id)"
        )
