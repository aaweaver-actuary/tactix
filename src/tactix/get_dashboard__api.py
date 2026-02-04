"""API handler for dashboard payloads."""

from typing import Annotated

from fastapi import Depends, Query

from tactix._resolve_dashboard_filters import _resolve_dashboard_filters
from tactix.build_dashboard_cache_key__api_cache import _dashboard_cache_key
from tactix.dashboard_query import DashboardQuery
from tactix.DashboardQueryFilters import DashboardQueryFilters
from tactix.get_cached_dashboard_payload__api_cache import _get_cached_dashboard_payload
from tactix.pipeline import get_dashboard_payload
from tactix.set_dashboard_cache__api_cache import _set_dashboard_cache


def get_dashboard(
    filters: Annotated[DashboardQueryFilters, Depends()],
    motif: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    """Return dashboard payload for the provided filters."""
    start_datetime, end_datetime, normalized_source, settings = _resolve_dashboard_filters(
        filters,
    )
    query = DashboardQuery(
        source=normalized_source,
        motif=motif,
        rating_bucket=filters.rating_bucket,
        time_control=filters.time_control,
        start_date=start_datetime,
        end_date=end_datetime,
    )
    cache_key = _dashboard_cache_key(settings, query)
    cached = _get_cached_dashboard_payload(cache_key)
    if cached is not None:
        return cached
    payload = get_dashboard_payload(query, settings)
    _set_dashboard_cache(cache_key, payload)
    return payload


__all__ = [
    "_get_cached_dashboard_payload",
    "get_dashboard",
    "get_dashboard_payload",
]
