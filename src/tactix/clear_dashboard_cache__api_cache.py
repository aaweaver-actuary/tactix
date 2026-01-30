from __future__ import annotations

from tactix.dashboard_cache_state__api_cache import _DASHBOARD_CACHE, _DASHBOARD_CACHE_LOCK


def _clear_dashboard_cache() -> None:
    with _DASHBOARD_CACHE_LOCK:
        _DASHBOARD_CACHE.clear()
