"""Initialize DuckDB schema objects."""

from __future__ import annotations

import duckdb

from tactix.db.duckdb_store import init_schema as _init_schema


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Initialize or migrate the schema for the connection."""
    _init_schema(conn)
