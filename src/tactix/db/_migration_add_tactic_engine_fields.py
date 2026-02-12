"""Add engine analysis columns to tactics."""

from __future__ import annotations

import duckdb

from tactix.db._migration_add_pipeline_views import _migration_add_pipeline_views


def _migration_add_tactic_engine_fields(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure tactics include best line and engine depth columns."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('tactics')").fetchall()}
    if "best_line_uci" not in columns:
        conn.execute("ALTER TABLE tactics ADD COLUMN best_line_uci TEXT")
    if "engine_depth" not in columns:
        conn.execute("ALTER TABLE tactics ADD COLUMN engine_depth INTEGER")
    _migration_add_pipeline_views(conn)
