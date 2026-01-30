from __future__ import annotations

from datetime import datetime

from tactix.build_dashboard_cache_key__api_cache import _dashboard_cache_key
from tactix.config import get_settings
from tactix.pipeline import get_dashboard_payload
from tactix.set_dashboard_cache__api_cache import _set_dashboard_cache


def _prime_dashboard_cache(
    source: str | None = None,
    motif: str | None = None,
    rating_bucket: str | None = None,
    time_control: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> None:
    settings = get_settings(source=source)
    payload = get_dashboard_payload(
        settings,
        source=source,
        motif=motif,
        rating_bucket=rating_bucket,
        time_control=time_control,
        start_date=start_date,
        end_date=end_date,
    )
    key = _dashboard_cache_key(
        settings,
        source,
        motif,
        rating_bucket,
        time_control,
        start_date,
        end_date,
    )
    _set_dashboard_cache(key, payload)
