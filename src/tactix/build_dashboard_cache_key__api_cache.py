from __future__ import annotations

from datetime import datetime

from tactix.coerce_cache_value__api_cache import _cache_value
from tactix.coerce_date_cache_value__api_cache import _date_cache_value


def _dashboard_cache_key(
    settings,
    source: str | None,
    motif: str | None,
    rating_bucket: str | None,
    time_control: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[object, ...]:
    return (
        settings.user,
        str(settings.duckdb_path),
        _cache_value(source),
        _cache_value(motif),
        _cache_value(rating_bucket),
        _cache_value(time_control),
        _date_cache_value(start_date),
        _date_cache_value(end_date),
    )
