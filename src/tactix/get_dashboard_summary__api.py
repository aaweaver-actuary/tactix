"""API handler for dashboard summary totals."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, Query

from tactix._resolve_dashboard_filters import _resolve_dashboard_filters
from tactix.dashboard_query import DashboardQuery
from tactix.dashboard_query_filters import DashboardQueryFilters
from tactix.db.duckdb_store import fetch_pipeline_table_counts, get_connection, init_schema


def dashboard_summary(  # pragma: no cover
    filters: Annotated[DashboardQueryFilters, Depends()],
    db_name: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    """Return dashboard summary totals for the provided filters."""
    start_datetime, end_datetime, normalized_source, settings = _resolve_dashboard_filters(
        filters,
    )
    if db_name:
        safe_name = Path(db_name).name
        filename = safe_name if safe_name.endswith(".duckdb") else f"{safe_name}.duckdb"
        settings.duckdb_path = settings.data_dir / filename
    conn = get_connection(settings.duckdb_path)
    try:
        init_schema(conn)
        summary = fetch_pipeline_table_counts(
            conn,
            DashboardQuery(
                source=normalized_source,
                rating_bucket=filters.rating_bucket,
                time_control=filters.time_control,
                start_date=start_datetime,
                end_date=end_datetime,
            ),
        )
    finally:
        conn.close()
    response_source = "all" if normalized_source is None else normalized_source
    return {
        "source": response_source,
        "summary": summary,
    }


__all__ = ["dashboard_summary"]
