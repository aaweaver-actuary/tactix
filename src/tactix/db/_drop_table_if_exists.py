"""Drop a DuckDB table when present."""

from __future__ import annotations

import duckdb


def _drop_table_if_exists(conn: duckdb.DuckDBPyConnection, table: str) -> None:
    """Drop a table if it exists."""
    conn.execute(f"DROP TABLE IF EXISTS {table}")
