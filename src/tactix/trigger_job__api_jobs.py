from __future__ import annotations

import time as time_module
from queue import Queue
from typing import Annotated

from fastapi import Query

from tactix.config import get_settings
from tactix.list_sources_for_cache_refresh__api_cache import _sources_for_cache_refresh
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async
from tactix.resolve_backfill_end_ms__airflow_jobs import _resolve_backfill_end_ms
from tactix.run_stream_job__job_stream import _run_stream_job


def _ignore_progress(_payload: dict[str, object]) -> None:
    return None


def trigger_job(
    job: Annotated[str, Query()] = "daily_game_sync",
    source: Annotated[str | None, Query()] = None,
    profile: Annotated[str | None, Query()] = None,
    backfill_start_ms: Annotated[int | None, Query(ge=0)] = None,
    backfill_end_ms: Annotated[int | None, Query(ge=0)] = None,
) -> dict[str, object]:
    settings = get_settings(source=source, profile=profile)
    queue: Queue[object] = Queue()
    triggered_at_ms = int(time_module.time() * 1000)
    effective_end_ms = _resolve_backfill_end_ms(
        backfill_start_ms,
        backfill_end_ms,
        triggered_at_ms,
    )
    result = _run_stream_job(
        settings,
        queue,
        job,
        source,
        profile,
        backfill_start_ms,
        effective_end_ms,
        triggered_at_ms,
        _ignore_progress,
    )
    if job in {"daily_game_sync", "refresh_metrics"}:
        _refresh_dashboard_cache_async(_sources_for_cache_refresh(source))
    return {"status": "ok", "job": job, "result": result}
