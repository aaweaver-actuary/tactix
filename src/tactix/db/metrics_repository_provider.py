"""Factory helpers for DuckDB metrics repository access."""

from __future__ import annotations

import duckdb

from tactix.db.duckdb_metrics_repository import (
    DuckDbMetricsRepository,
    default_metrics_dependencies,
)


def metrics_repository(conn: duckdb.DuckDBPyConnection) -> DuckDbMetricsRepository:
    """Return a DuckDbMetricsRepository bound to the provided connection."""
    return DuckDbMetricsRepository(conn, dependencies=default_metrics_dependencies())


def update_metrics_summary(conn: duckdb.DuckDBPyConnection) -> None:
    """Recompute metrics summary rows."""
    metrics_repository(conn).update_metrics_summary()
