"""In-memory dashboard cache state."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock

_DASHBOARD_CACHE_TTL_S = 300
_DASHBOARD_CACHE_MAX_ENTRIES = 32
_DASHBOARD_CACHE: OrderedDict[tuple[object, ...], tuple[float, dict[str, object]]] = OrderedDict()
_DASHBOARD_CACHE_LOCK = Lock()
