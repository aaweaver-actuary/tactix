from typing import Annotated

from fastapi import Depends

from tactix._resolve_dashboard_filters import _resolve_dashboard_filters
from tactix.DashboardQueryFilters import DashboardQueryFilters
from tactix.db.duckdb_store import fetch_motif_stats, fetch_version, get_connection, init_schema


def motif_stats(
    filters: Annotated[DashboardQueryFilters, Depends()],
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
        "motifs": fetch_motif_stats(
            conn,
            source=normalized_source,
            rating_bucket=filters.rating_bucket,
            time_control=filters.time_control,
            start_date=start_datetime,
            end_date=end_datetime,
        ),
    }
