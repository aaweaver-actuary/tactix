"""Ensure raw PGN tables include versioning columns."""

from __future__ import annotations

import duckdb


def _migration_raw_pgns_versioning(conn: duckdb.DuckDBPyConnection) -> None:
    """Add versioning columns to raw PGN rows when missing."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('raw_pgns')").fetchall()}
    if "pgn_hash" not in columns:
        conn.execute("ALTER TABLE raw_pgns ADD COLUMN pgn_hash TEXT")
    if "pgn_version" not in columns:
        conn.execute("ALTER TABLE raw_pgns ADD COLUMN pgn_version INTEGER")
        conn.execute("UPDATE raw_pgns SET pgn_version = 1 WHERE pgn_version IS NULL")
