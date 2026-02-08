"""Fetch metrics summary rows from DuckDB."""

from __future__ import annotations

import duckdb

from tactix.dashboard_query import DashboardQuery
from tactix.db.duckdb_store import fetch_metrics as _fetch_metrics


def fetch_metrics(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> list[dict[str, object]]:
    """Fetch metrics summary rows for the provided filters."""
    return _fetch_metrics(conn, query, filters=filters, **legacy)
