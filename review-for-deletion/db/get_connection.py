"""Open DuckDB connections."""

from __future__ import annotations

from pathlib import Path

import duckdb

from tactix.db.duckdb_store import get_connection as _get_connection


def get_connection(db_path: Path | str) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection for the configured path."""
    return _get_connection(db_path)
