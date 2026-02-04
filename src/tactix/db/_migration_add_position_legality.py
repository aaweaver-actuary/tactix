"""Add legality column to positions."""

from __future__ import annotations

import duckdb


def _migration_add_position_legality(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure positions include legality metadata."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('positions')").fetchall()}
    if "is_legal" not in columns:
        conn.execute("ALTER TABLE positions ADD COLUMN is_legal BOOLEAN")
