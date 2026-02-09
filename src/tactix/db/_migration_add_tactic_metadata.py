"""Add tactic metadata columns to tactics."""

from __future__ import annotations

import duckdb


def _migration_add_tactic_metadata(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure tactic metadata columns exist."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('tactics')").fetchall()}
    if "tactic_piece" not in columns:
        conn.execute("ALTER TABLE tactics ADD COLUMN tactic_piece TEXT")
    if "mate_type" not in columns:
        conn.execute("ALTER TABLE tactics ADD COLUMN mate_type TEXT")
