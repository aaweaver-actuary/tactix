"""Add hanging target metadata columns to tactics."""

from __future__ import annotations

import duckdb

from tactix.db._migration_add_pipeline_views import _migration_add_pipeline_views


def _migration_add_tactic_targets(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure target metadata columns exist on tactics."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('tactics')").fetchall()}
    if "target_piece" not in columns:
        conn.execute("ALTER TABLE tactics ADD COLUMN target_piece TEXT")
    if "target_square" not in columns:
        conn.execute("ALTER TABLE tactics ADD COLUMN target_square TEXT")
    _migration_add_pipeline_views(conn)
