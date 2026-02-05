from __future__ import annotations

from collections.abc import Callable
from queue import Queue
from typing import cast

from tactix.check_airflow_enabled__airflow_settings import _airflow_enabled
from tactix.config import Settings
from tactix.DailySyncStartContext import DailyGameSyncRequest
from tactix.legacy_args import apply_legacy_args, apply_legacy_kwargs, init_legacy_values
from tactix.pipeline import run_daily_game_sync, run_migrations, run_refresh_metrics
from tactix.define_pipeline_state__pipeline import ProgressCallback
from tactix.raise_unsupported_job__api_jobs import _raise_unsupported_job
from tactix.run_airflow_daily_sync_job__job_stream import _run_airflow_daily_sync_job
from tactix.stream_job_context import (
    BACKFILL_WINDOW_KEYS,
    AirflowDailySyncContext,
    StreamJobRunContext,
    build_stream_job_request_from_values,
)
from tactix.utils.logger import funclogger


@funclogger
def _noop_progress(_payload: dict[str, object]) -> None:
    return None


@funclogger
def _collect_stream_job_values(
    args: tuple[object, ...],
    legacy: dict[str, object],
) -> dict[str, object]:
    ordered_keys = ("queue", "job", *BACKFILL_WINDOW_KEYS, "progress")
    values = init_legacy_values(ordered_keys)
    apply_legacy_kwargs(values, ordered_keys, legacy)
    apply_legacy_args(values, ordered_keys, args)
    return values


@funclogger
def _build_stream_job_context(
    settings: Settings,
    values: dict[str, object],
) -> StreamJobRunContext:
    if values["queue"] is None or values["job"] is None or values["triggered_at_ms"] is None:
        raise TypeError("settings, queue, job, and triggered_at_ms are required")
    queue = cast(Queue[object], values["queue"])
    triggered_at_ms = cast(int, values["triggered_at_ms"])
    progress = cast(ProgressCallback | None, values["progress"])
    if progress is None:
        progress = _noop_progress
    request = build_stream_job_request_from_values(values)
    return StreamJobRunContext(
        settings=settings,
        queue=queue,
        job=request.job,
        source=request.source,
        profile=request.profile,
        backfill_start_ms=request.backfill_start_ms,
        backfill_end_ms=request.backfill_end_ms,
        triggered_at_ms=triggered_at_ms,
        progress=progress,
    )


@funclogger
def _run_stream_job(
    context: StreamJobRunContext | Settings,
    *args: object,
    **legacy: object,
) -> dict[str, object]:
    if isinstance(context, StreamJobRunContext):
        ctx = context
    else:
        values = _collect_stream_job_values(args, legacy)
        ctx = _build_stream_job_context(context, values)

    def run_daily_sync() -> dict[str, object]:
        if _airflow_enabled(ctx.settings):
            return _run_airflow_daily_sync_job(
                AirflowDailySyncContext(
                    settings=ctx.settings,
                    queue=ctx.queue,
                    job=ctx.job,
                    source=ctx.source,
                    profile=ctx.profile,
                    backfill_start_ms=ctx.backfill_start_ms,
                    backfill_end_ms=ctx.backfill_end_ms,
                    triggered_at_ms=ctx.triggered_at_ms,
                )
            )
        return run_daily_game_sync(
            DailyGameSyncRequest(
                settings=ctx.settings,
                source=ctx.source,
                progress=ctx.progress,
                profile=ctx.profile,
                window_start_ms=ctx.backfill_start_ms,
                window_end_ms=ctx.backfill_end_ms,
            )
        )

    handlers: dict[str, Callable[[], dict[str, object]]] = {
        "daily_game_sync": run_daily_sync,
        "refresh_metrics": lambda: run_refresh_metrics(
            ctx.settings,
            source=ctx.source,
            progress=ctx.progress,
        ),
        "migrations": lambda: run_migrations(
            ctx.settings,
            source=ctx.source,
            progress=ctx.progress,
        ),
    }
    handler = handlers.get(ctx.job)
    if handler is None:
        _raise_unsupported_job(ctx.job)
    return cast(Callable[[], dict[str, object]], handler)()
