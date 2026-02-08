"""Factory helpers for DuckDB dashboard repository access."""

from __future__ import annotations

import duckdb

from tactix.dashboard_query import DashboardQuery
from tactix.db.duckdb_dashboard_repository import (
    DuckDbDashboardRepository,
    default_dashboard_repository_dependencies,
)


def dashboard_repository(conn: duckdb.DuckDBPyConnection) -> DuckDbDashboardRepository:
    """Return a DuckDbDashboardRepository bound to the provided connection."""
    return DuckDbDashboardRepository(
        conn,
        dependencies=default_dashboard_repository_dependencies(),
    )


def fetch_pipeline_table_counts(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> dict[str, int]:
    """Return per-table counts for pipeline verification."""
    return dashboard_repository(conn).fetch_pipeline_table_counts(
        query,
        filters=filters,
        **legacy,
    )


def fetch_opportunity_motif_counts(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> dict[str, int]:
    """Return motif counts for opportunities in the dashboard range."""
    return dashboard_repository(conn).fetch_opportunity_motif_counts(
        query,
        filters=filters,
        **legacy,
    )


def fetch_metrics(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> list[dict[str, object]]:
    """Fetch metrics summary rows with optional filters."""
    return dashboard_repository(conn).fetch_metrics(
        query,
        filters=filters,
        **legacy,
    )


def fetch_motif_stats(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> list[dict[str, object]]:
    """Return motif breakdown metrics."""
    rows = fetch_metrics(conn, query, filters=filters, **legacy)
    return [row for row in rows if row.get("metric_type") == "motif_breakdown"]


def fetch_trend_stats(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> list[dict[str, object]]:
    """Return trend metrics rows."""
    rows = fetch_metrics(conn, query, filters=filters, **legacy)
    return [row for row in rows if row.get("metric_type") == "trend"]


def fetch_recent_games(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    limit: int = 20,
    user: str | None = None,
    **legacy: object,
) -> list[dict[str, object]]:
    """Return recent games for dashboard display."""
    return dashboard_repository(conn).fetch_recent_games(
        query,
        limit=limit,
        user=user,
        **legacy,
    )


def fetch_recent_positions(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    limit: int = 20,
    **legacy: object,
) -> list[dict[str, object]]:
    """Return recent positions for dashboard display."""
    return dashboard_repository(conn).fetch_recent_positions(
        query,
        limit=limit,
        **legacy,
    )


def fetch_recent_tactics(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    limit: int = 20,
    **legacy: object,
) -> list[dict[str, object]]:
    """Return recent tactics for dashboard display."""
    return dashboard_repository(conn).fetch_recent_tactics(
        query,
        limit=limit,
        **legacy,
    )
