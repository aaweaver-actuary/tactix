"""Build dashboard stats payloads for API responses."""

from __future__ import annotations

from collections.abc import Callable

from tactix._resolve_dashboard_filters import _resolve_dashboard_filters
from tactix.dashboard_query_filters import DashboardQueryFilters
from tactix.db.duckdb_store import fetch_version, get_connection, init_schema


def _build_dashboard_stats_payload(
    filters: DashboardQueryFilters,
    stats_fetcher: Callable[..., object],
    stats_key: str,
) -> dict[str, object]:
    start_datetime, end_datetime, normalized_source, settings = _resolve_dashboard_filters(
        filters,
    )
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    response_source = "all" if normalized_source is None else normalized_source
    return {
        "source": response_source,
        "metrics_version": fetch_version(conn),
        stats_key: stats_fetcher(
            conn,
            source=normalized_source,
            rating_bucket=filters.rating_bucket,
            time_control=filters.time_control,
            start_date=start_datetime,
            end_date=end_datetime,
        ),
    }
