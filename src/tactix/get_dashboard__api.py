from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Query

from tactix.build_dashboard_cache_key__api_cache import _dashboard_cache_key
from tactix.coerce_date_to_datetime__datetime import _coerce_date_to_datetime
from tactix.config import get_settings
from tactix.get_cached_dashboard_payload__api_cache import _get_cached_dashboard_payload
from tactix.normalize_source__source import _normalize_source
from tactix.pipeline import get_dashboard_payload
from tactix.set_dashboard_cache__api_cache import _set_dashboard_cache


def dashboard(
    source: Annotated[str | None, Query()] = None,
    motif: Annotated[str | None, Query()] = None,
    rating_bucket: Annotated[str | None, Query()] = None,
    time_control: Annotated[str | None, Query()] = None,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> dict[str, object]:
    start_datetime = _coerce_date_to_datetime(start_date)
    end_datetime = _coerce_date_to_datetime(end_date, end_of_day=True)
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    cache_key = _dashboard_cache_key(
        settings,
        normalized_source,
        motif,
        rating_bucket,
        time_control,
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
        rating_bucket=rating_bucket,
        time_control=time_control,
        start_date=start_datetime,
        end_date=end_datetime,
    )
    _set_dashboard_cache(cache_key, payload)
    return payload
