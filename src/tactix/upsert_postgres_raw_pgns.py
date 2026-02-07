"""Legacy wrapper for Postgres raw PGN upsert operations."""

from collections.abc import Mapping

from psycopg2.extensions import connection as PgConnection  # noqa: N812

from tactix.db.postgres_raw_pgn_repository import PostgresRawPgnRepository


def upsert_postgres_raw_pgns(
    conn: PgConnection,
    rows: list[Mapping[str, object]],
) -> int:
    """Insert raw PGN rows inside a transaction."""
    return PostgresRawPgnRepository(conn).upsert_raw_pgns(rows)
