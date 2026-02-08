"""Add explanation column to tactics."""

from __future__ import annotations

import duckdb


def _migration_add_tactic_explanations(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure tactics include explanation text."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('tactics')").fetchall()}
    if "explanation" not in columns:
        conn.execute("ALTER TABLE tactics ADD COLUMN explanation TEXT")
