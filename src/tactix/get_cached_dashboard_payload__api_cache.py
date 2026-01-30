from __future__ import annotations

import time as time_module

from tactix.dashboard_cache_state__api_cache import (
    _DASHBOARD_CACHE,
    _DASHBOARD_CACHE_LOCK,
    _DASHBOARD_CACHE_TTL_S,
)


def _get_cached_dashboard_payload(key: tuple[object, ...]) -> dict[str, object] | None:
    now = time_module.time()
    with _DASHBOARD_CACHE_LOCK:
        cached = _DASHBOARD_CACHE.get(key)
        if not cached:
            return None
        cached_at, payload = cached
        if now - cached_at > _DASHBOARD_CACHE_TTL_S:
            _DASHBOARD_CACHE.pop(key, None)
            return None
        _DASHBOARD_CACHE.move_to_end(key)
        return payload
