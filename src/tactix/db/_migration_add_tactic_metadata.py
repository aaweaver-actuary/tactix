"""Add tactic metadata columns to tactics."""

from __future__ import annotations

import duckdb


def _migration_add_tactic_metadata(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure tactic metadata columns exist."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('tactics')").fetchall()}
    for column_name in ("tactic_piece", "mate_type", "target_piece", "target_square"):
        if column_name in columns:
            continue
        conn.execute(f"ALTER TABLE tactics ADD COLUMN {column_name} TEXT")
