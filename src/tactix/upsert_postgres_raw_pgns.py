"""Persist raw PGN rows into Postgres."""

from collections.abc import Mapping

import psycopg2
from psycopg2.extensions import connection as PgConnection  # noqa: N812

from tactix._upsert_postgres_raw_pgn_rows import _upsert_postgres_raw_pgn_rows


def upsert_postgres_raw_pgns(
    conn: PgConnection,
    rows: list[Mapping[str, object]],
) -> int:
    """Insert raw PGN rows inside a transaction."""
    if not rows:
        return 0
    autocommit_state = conn.autocommit
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            inserted = _upsert_postgres_raw_pgn_rows(cur, rows)
    except psycopg2.Error:
        conn.rollback()
        raise
    else:
        conn.commit()
        return inserted
    finally:
        conn.autocommit = autocommit_state
