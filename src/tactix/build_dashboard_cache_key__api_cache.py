from __future__ import annotations

from datetime import datetime
from typing import cast

from tactix.coerce_cache_value__api_cache import _cache_value
from tactix.coerce_date_cache_value__api_cache import _date_cache_value
from tactix.dashboard_query import DashboardQuery, resolve_dashboard_query
from tactix.legacy_args import apply_legacy_args, apply_legacy_kwargs, init_legacy_values


def _dashboard_cache_key(
    settings,
    *args: object,
    query: DashboardQuery | str | None = None,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> tuple[object, ...]:
    ordered_keys = (
        "query",
        "source",
        "motif",
        "rating_bucket",
        "time_control",
        "start_date",
        "end_date",
    )
    values = init_legacy_values(
        ordered_keys,
        {"query": query} if query is not None else None,
    )
    apply_legacy_kwargs(values, ordered_keys[1:], legacy)
    apply_legacy_args(values, ordered_keys, args)
    resolved = resolve_dashboard_query(
        cast(DashboardQuery | str | None, values["query"]),
        filters=filters,
        source=cast(str | None, values["source"]),
        motif=cast(str | None, values["motif"]),
        rating_bucket=cast(str | None, values["rating_bucket"]),
        time_control=cast(str | None, values["time_control"]),
        start_date=cast(datetime | None, values["start_date"]),
        end_date=cast(datetime | None, values["end_date"]),
    )
    return (
        settings.user,
        str(settings.duckdb_path),
        _cache_value(resolved.source),
        _cache_value(resolved.motif),
        _cache_value(resolved.rating_bucket),
        _cache_value(resolved.time_control),
        _date_cache_value(resolved.start_date),
        _date_cache_value(resolved.end_date),
    )
