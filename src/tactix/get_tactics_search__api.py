"""API handler for tactics search."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from tactix.coerce_date_to_datetime__datetime import _coerce_date_to_datetime
from tactix.config import get_settings
from tactix.dashboard_query import DashboardQuery
from tactix.db.duckdb_store import fetch_recent_tactics, get_connection, init_schema
from tactix.normalize_source__source import _normalize_source
from tactix.TacticsSearchFilters import TacticsSearchFilters


def tactics_search(
    filters: Annotated[TacticsSearchFilters, Depends()],
    limit: int = Query(20, ge=1, le=200),  # noqa: B008
) -> dict[str, object]:
    """Fetch recent tactics that match the given filters."""
    normalized_source = _normalize_source(filters.source)
    settings = get_settings(source=normalized_source)
    start_datetime = _coerce_date_to_datetime(filters.start_date)
    end_datetime = _coerce_date_to_datetime(filters.end_date, end_of_day=True)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    tactics = fetch_recent_tactics(
        conn,
        DashboardQuery(
            source=normalized_source,
            motif=filters.motif,
            rating_bucket=filters.rating_bucket,
            time_control=filters.time_control,
            start_date=start_datetime,
            end_date=end_datetime,
        ),
        limit=limit,
    )
    response_source = "all" if normalized_source is None else normalized_source
    return {"source": response_source, "limit": limit, "tactics": tactics}
