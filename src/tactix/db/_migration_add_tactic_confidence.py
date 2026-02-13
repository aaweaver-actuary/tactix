"""Add confidence column to tactics."""

from __future__ import annotations

import duckdb

from tactix.db._migration_add_pipeline_views import _migration_add_pipeline_views


def _migration_add_tactic_confidence(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure tactics include confidence column."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('tactics')").fetchall()}
    if "confidence" not in columns:
        conn.execute("ALTER TABLE tactics ADD COLUMN confidence TEXT")
    _migration_add_pipeline_views(conn)
