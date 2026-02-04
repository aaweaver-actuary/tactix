"""API handler for trend stats."""

from typing import Annotated

from fastapi import Depends

from tactix.build_dashboard_stats_payload__api import _build_dashboard_stats_payload
from tactix.dashboard_query_filters import DashboardQueryFilters
from tactix.db.duckdb_store import fetch_trend_stats


def trend_stats(
    filters: Annotated[DashboardQueryFilters, Depends()],
) -> dict[str, object]:
    """Return trend stats payload for the provided filters."""
    return _build_dashboard_stats_payload(filters, fetch_trend_stats, "trends")
