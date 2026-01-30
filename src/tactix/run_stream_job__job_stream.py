from __future__ import annotations

from collections.abc import Callable
from queue import Queue
from typing import cast

from tactix.check_airflow_enabled__airflow_settings import _airflow_enabled
from tactix.config import Settings
from tactix.pipeline import run_daily_game_sync, run_migrations, run_refresh_metrics
from tactix.raise_unsupported_job__api_jobs import _raise_unsupported_job
from tactix.run_airflow_daily_sync_job__job_stream import _run_airflow_daily_sync_job


def _run_stream_job(
    settings: Settings,
    queue: Queue[object],
    job: str,
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
    triggered_at_ms: int,
    progress: Callable[[dict[str, object]], None],
) -> dict[str, object]:
    def run_daily_sync() -> dict[str, object]:
        if _airflow_enabled(settings):
            return _run_airflow_daily_sync_job(
                settings,
                queue,
                job,
                source,
                profile,
                backfill_start_ms,
                backfill_end_ms,
                triggered_at_ms,
            )
        return run_daily_game_sync(
            settings,
            source=source,
            progress=progress,
            profile=profile,
            window_start_ms=backfill_start_ms,
            window_end_ms=backfill_end_ms,
        )

    handlers: dict[str, Callable[[], dict[str, object]]] = {
        "daily_game_sync": run_daily_sync,
        "refresh_metrics": lambda: run_refresh_metrics(
            settings,
            source=source,
            progress=progress,
        ),
        "migrations": lambda: run_migrations(settings, source=source, progress=progress),
    }
    handler = handlers.get(job)
    if handler is None:
        _raise_unsupported_job(job)
    return cast(Callable[[], dict[str, object]], handler)()
