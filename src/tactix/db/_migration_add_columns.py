"""Add missing columns to raw PGN tables."""

from __future__ import annotations

import duckdb


def _migration_add_columns(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure recent columns exist on raw PGN rows."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('raw_pgns')").fetchall()}
    if "user_rating" not in columns:
        conn.execute("ALTER TABLE raw_pgns ADD COLUMN user_rating INTEGER")
    if "time_control" not in columns:
        conn.execute("ALTER TABLE raw_pgns ADD COLUMN time_control TEXT")
    if "ingested_at" not in columns:
        conn.execute("ALTER TABLE raw_pgns ADD COLUMN ingested_at TIMESTAMP")
    if "cursor" not in columns:
        conn.execute("ALTER TABLE raw_pgns ADD COLUMN cursor TEXT")
    if "last_timestamp_ms" not in columns:
        conn.execute("ALTER TABLE raw_pgns ADD COLUMN last_timestamp_ms BIGINT")
