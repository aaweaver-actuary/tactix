from __future__ import annotations

import time as time_module
from typing import Annotated

from fastapi import HTTPException, Query

from tactix.check_airflow_enabled__airflow_settings import _airflow_enabled
from tactix.config import get_settings
from tactix.normalize_source__source import _normalize_source
from tactix.resolve_backfill_end_ms__airflow_jobs import _resolve_backfill_end_ms

_SUPPORTED_JOBS = {
    "daily_game_sync",
    "refresh_metrics",
    "migrations",
}


def get_job_status(
    job_id: str,
    source: Annotated[str | None, Query()] = None,
    profile: Annotated[str | None, Query()] = None,
    backfill_start_ms: Annotated[int | None, Query(ge=0)] = None,
    backfill_end_ms: Annotated[int | None, Query(ge=0)] = None,
) -> dict[str, object]:
    if job_id not in _SUPPORTED_JOBS:
        raise HTTPException(status_code=404, detail="Job not supported")
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source, profile=profile)
    requested_at_ms = int(time_module.time() * 1000)
    effective_end_ms = _resolve_backfill_end_ms(
        backfill_start_ms,
        backfill_end_ms,
        requested_at_ms,
    )
    return {
        "status": "ok",
        "job": job_id,
        "job_id": job_id,
        "source": normalized_source,
        "profile": profile,
        "backfill_start_ms": backfill_start_ms,
        "backfill_end_ms": effective_end_ms,
        "requested_at_ms": requested_at_ms,
        "airflow_enabled": _airflow_enabled(settings),
    }
