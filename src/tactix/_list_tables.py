"""List tables from a Postgres schema."""

from psycopg2.extensions import connection as PgConnection  # noqa: N812


def _list_tables(conn: PgConnection, schema: str) -> list[str]:
    """Return table names for the provided schema."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
            """,
            (schema,),
        )
        return [row[0] for row in cur.fetchall()]
