"""Add missing columns to raw PGN tables."""

from __future__ import annotations

import duckdb


def _migration_add_columns(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure recent columns exist on raw PGN rows."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('raw_pgns')").fetchall()}
    additions = {
        "user_rating": "ALTER TABLE raw_pgns ADD COLUMN user_rating INTEGER",
        "time_control": "ALTER TABLE raw_pgns ADD COLUMN time_control TEXT",
        "ingested_at": "ALTER TABLE raw_pgns ADD COLUMN ingested_at TIMESTAMP",
        "cursor": "ALTER TABLE raw_pgns ADD COLUMN cursor TEXT",
        "last_timestamp_ms": "ALTER TABLE raw_pgns ADD COLUMN last_timestamp_ms BIGINT",
    }
    for column, statement in additions.items():
        if column not in columns:
            conn.execute(statement)
