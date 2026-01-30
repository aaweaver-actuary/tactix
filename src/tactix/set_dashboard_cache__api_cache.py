from __future__ import annotations

import time as time_module

from tactix.dashboard_cache_state__api_cache import (
    _DASHBOARD_CACHE,
    _DASHBOARD_CACHE_LOCK,
    _DASHBOARD_CACHE_MAX_ENTRIES,
)


def _set_dashboard_cache(key: tuple[object, ...], payload: dict[str, object]) -> None:
    with _DASHBOARD_CACHE_LOCK:
        _DASHBOARD_CACHE[key] = (time_module.time(), payload)
        _DASHBOARD_CACHE.move_to_end(key)
        while len(_DASHBOARD_CACHE) > _DASHBOARD_CACHE_MAX_ENTRIES:
            _DASHBOARD_CACHE.popitem(last=False)
