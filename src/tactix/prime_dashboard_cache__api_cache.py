from __future__ import annotations

from tactix.build_dashboard_cache_key__api_cache import _dashboard_cache_key
from tactix.config import get_settings
from tactix.dashboard_query import DashboardQuery
from tactix.pipeline import get_dashboard_payload
from tactix.set_dashboard_cache__api_cache import _set_dashboard_cache


def _prime_dashboard_cache(
    query: DashboardQuery,
) -> None:
    settings = get_settings(source=query.source)
    payload = get_dashboard_payload(query, settings)
    key = _dashboard_cache_key(settings, query)
    _set_dashboard_cache(key, payload)
