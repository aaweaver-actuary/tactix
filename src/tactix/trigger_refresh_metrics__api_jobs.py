from __future__ import annotations

from typing import Annotated

from fastapi import Query

from tactix.config import get_settings
from tactix.list_sources_for_cache_refresh__api_cache import _sources_for_cache_refresh
from tactix.pipeline import run_refresh_metrics
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async


def trigger_refresh_metrics(
    source: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    result = run_refresh_metrics(get_settings(source=source), source=source)
    _refresh_dashboard_cache_async(_sources_for_cache_refresh(source))
    return {"status": "ok", "result": result}
