"""Resolve dashboard query inputs for DuckDB helpers."""

from __future__ import annotations

from tactix.dashboard_query import DashboardQuery, resolve_dashboard_query


def _resolve_dashboard_query(
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> DashboardQuery:
    """Resolve query inputs to a DashboardQuery instance."""
    return resolve_dashboard_query(query, filters=filters, **legacy)
