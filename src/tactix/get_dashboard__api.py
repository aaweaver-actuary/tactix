from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import Depends, Query

from tactix.build_dashboard_cache_key__api_cache import _dashboard_cache_key
from tactix.coerce_date_to_datetime__datetime import _coerce_date_to_datetime
from tactix.config import Settings, get_settings
from tactix.db.duckdb_store import (
    fetch_motif_stats,
    fetch_trend_stats,
    fetch_version,
    get_connection,
    init_schema,
)
from tactix.get_cached_dashboard_payload__api_cache import _get_cached_dashboard_payload
from tactix.normalize_source__source import _normalize_source
from tactix.pipeline import get_dashboard_payload
from tactix.set_dashboard_cache__api_cache import _set_dashboard_cache


class DashboardQueryFilters:
    def __init__(
        self,
        source: Annotated[str | None, Query()] = None,
        rating_bucket: Annotated[str | None, Query()] = None,
        time_control: Annotated[str | None, Query()] = None,
        start_date: Annotated[date | None, Query()] = None,
        end_date: Annotated[date | None, Query()] = None,
    ) -> None:
        self.source = source
        self.rating_bucket = rating_bucket
        self.time_control = time_control
        self.start_date = start_date
        self.end_date = end_date


def _resolve_dashboard_filters(
    filters: DashboardQueryFilters,
) -> tuple[datetime | None, datetime | None, str | None, Settings]:
    start_datetime = _coerce_date_to_datetime(filters.start_date)
    end_datetime = _coerce_date_to_datetime(filters.end_date, end_of_day=True)
    normalized_source = _normalize_source(filters.source)
    settings = get_settings(source=normalized_source)
    return start_datetime, end_datetime, normalized_source, settings


def dashboard(
    filters: Annotated[DashboardQueryFilters, Depends()],
    motif: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    start_datetime, end_datetime, normalized_source, settings = _resolve_dashboard_filters(
        filters,
    )
    cache_key = _dashboard_cache_key(
        settings,
        normalized_source,
        motif,
        filters.rating_bucket,
        filters.time_control,
        start_datetime,
        end_datetime,
    )
    cached = _get_cached_dashboard_payload(cache_key)
    if cached is not None:
        return cached
    payload = get_dashboard_payload(
        settings,
        source=normalized_source,
        motif=motif,
        rating_bucket=filters.rating_bucket,
        time_control=filters.time_control,
        start_date=start_datetime,
        end_date=end_datetime,
    )
    _set_dashboard_cache(cache_key, payload)
    return payload


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


def trend_stats(
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
        "trends": fetch_trend_stats(
            conn,
            source=normalized_source,
            rating_bucket=filters.rating_bucket,
            time_control=filters.time_control,
            start_date=start_datetime,
            end_date=end_datetime,
        ),
    }
