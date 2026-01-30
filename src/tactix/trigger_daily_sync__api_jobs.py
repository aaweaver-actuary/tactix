from __future__ import annotations

from typing import Annotated

from fastapi import Query

from tactix.config import get_settings
from tactix.list_sources_for_cache_refresh__api_cache import _sources_for_cache_refresh
from tactix.pipeline import run_daily_game_sync
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async


def trigger_daily_sync(
    source: Annotated[str | None, Query()] = None,
    backfill_start_ms: Annotated[int | None, Query(ge=0)] = None,
    backfill_end_ms: Annotated[int | None, Query(ge=0)] = None,
    profile: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    result = run_daily_game_sync(
        get_settings(source=source, profile=profile),
        source=source,
        window_start_ms=backfill_start_ms,
        window_end_ms=backfill_end_ms,
        profile=profile,
    )
    _refresh_dashboard_cache_async(_sources_for_cache_refresh(source))
    return {"status": "ok", "result": result}
