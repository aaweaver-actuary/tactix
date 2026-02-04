"""Job stream contexts, helpers, and API endpoints."""

from __future__ import annotations

import time as time_module
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from threading import Thread
from typing import Annotated, cast

from fastapi import Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from tactix._resolve_dashboard_filters import _resolve_dashboard_filters
from tactix.airflow_daily_sync_context import AirflowDailySyncTriggerContext
from tactix.api_logger__tactix import logger
from tactix.check_airflow_enabled__airflow_settings import _airflow_enabled
from tactix.config import Settings, get_settings
from tactix.DailySyncStartContext import DailyGameSyncRequest
from tactix.dashboard_query import DashboardQuery
from tactix.dashboard_query_filters import DashboardQueryFilters
from tactix.ensure_airflow_success__airflow_jobs import _ensure_airflow_success
from tactix.format_sse__api_streaming import _format_sse
from tactix.get_airflow_state__airflow_jobs import _airflow_state
from tactix.legacy_args import apply_legacy_args, apply_legacy_kwargs, init_legacy_values
from tactix.list_sources_for_cache_refresh__api_cache import _sources_for_cache_refresh
from tactix.normalize_source__source import _normalize_source
from tactix.pipeline import (
    get_dashboard_payload,
    run_daily_game_sync,
    run_migrations,
    run_refresh_metrics,
)
from tactix.pipeline_state__pipeline import ProgressCallback
from tactix.raise_unsupported_job__api_jobs import _raise_unsupported_job
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async
from tactix.resolve_backfill_end_ms__airflow_jobs import _resolve_backfill_end_ms
from tactix.trigger_airflow_daily_sync__airflow_jobs import _trigger_airflow_daily_sync
from tactix.utils import funclogger


@dataclass(frozen=True)
class StreamJobRequest:
    """Incoming stream job request parameters."""

    job: str
    source: str | None
    profile: str | None
    backfill_start_ms: int | None
    backfill_end_ms: int | None


@dataclass(frozen=True)
class BackfillWindow:
    """Common backfill window parameters."""

    source: str | None
    profile: str | None
    backfill_start_ms: int | None
    backfill_end_ms: int | None
    triggered_at_ms: int


@dataclass(frozen=True)
class StreamJobWorkerContext:
    """Context for streaming job worker execution."""

    settings: Settings
    queue: Queue[object]
    sentinel: object
    job: str
    window: BackfillWindow

    @property
    def source(self) -> str | None:
        return self.window.source

    @property
    def profile(self) -> str | None:
        return self.window.profile

    @property
    def backfill_start_ms(self) -> int | None:
        return self.window.backfill_start_ms

    @property
    def backfill_end_ms(self) -> int | None:
        return self.window.backfill_end_ms

    @property
    def triggered_at_ms(self) -> int:
        return self.window.triggered_at_ms


@dataclass(frozen=True)
class StreamJobRunContext:
    """Context for executing a stream job run."""

    settings: Settings
    queue: Queue[object]
    job: str
    window: BackfillWindow
    progress: Callable[[dict[str, object]], None]

    @property
    def source(self) -> str | None:
        return self.window.source

    @property
    def profile(self) -> str | None:
        return self.window.profile

    @property
    def backfill_start_ms(self) -> int | None:
        return self.window.backfill_start_ms

    @property
    def backfill_end_ms(self) -> int | None:
        return self.window.backfill_end_ms

    @property
    def triggered_at_ms(self) -> int:
        return self.window.triggered_at_ms


@dataclass(frozen=True)
class AirflowDailySyncContext:
    """Context for airflow daily sync jobs."""

    settings: Settings
    queue: Queue[object]
    job: str
    window: BackfillWindow

    @property
    def source(self) -> str | None:
        return self.window.source

    @property
    def profile(self) -> str | None:
        return self.window.profile

    @property
    def backfill_start_ms(self) -> int | None:
        return self.window.backfill_start_ms

    @property
    def backfill_end_ms(self) -> int | None:
        return self.window.backfill_end_ms

    @property
    def triggered_at_ms(self) -> int:
        return self.window.triggered_at_ms


@dataclass(frozen=True)
class MetricsFilters:
    """Filters used for streaming metrics results."""

    normalized_source: str | None
    motif: str | None
    rating_bucket: str | None
    time_control: str | None
    start_date: datetime | None
    end_date: datetime | None


@dataclass(frozen=True)
class MetricsStreamContext:
    """Context for streaming metrics results."""

    queue: Queue[object]
    sentinel: object
    settings: Settings
    filters: MetricsFilters

    @property
    def normalized_source(self) -> str | None:
        return self.filters.normalized_source

    @property
    def motif(self) -> str | None:
        return self.filters.motif

    @property
    def rating_bucket(self) -> str | None:
        return self.filters.rating_bucket

    @property
    def time_control(self) -> str | None:
        return self.filters.time_control

    @property
    def start_date(self) -> datetime | None:
        return self.filters.start_date

    @property
    def end_date(self) -> datetime | None:
        return self.filters.end_date


@funclogger
def build_stream_job_kwargs(
    *,
    job: str,
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
) -> dict[str, object]:
    """Build a kwargs dict for stream job contexts."""
    return {
        "job": job,
        "source": source,
        "profile": profile,
        "backfill_start_ms": backfill_start_ms,
        "backfill_end_ms": backfill_end_ms,
    }


@funclogger
def build_stream_job_request(
    *,
    job: str,
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
) -> StreamJobRequest:
    """Create a StreamJobRequest from common inputs."""
    return StreamJobRequest(
        **build_stream_job_kwargs(
            job=job,
            source=source,
            profile=profile,
            backfill_start_ms=backfill_start_ms,
            backfill_end_ms=backfill_end_ms,
        )
    )


def build_stream_job_request_from_values(
    values: dict[str, object],
) -> StreamJobRequest:
    """Create a StreamJobRequest from a values mapping."""
    return StreamJobRequest(
        job=cast(str, values["job"]),
        source=cast(str | None, values["source"]),
        profile=cast(str | None, values["profile"]),
        backfill_start_ms=cast(int | None, values["backfill_start_ms"]),
        backfill_end_ms=cast(int | None, values["backfill_end_ms"]),
    )


BACKFILL_WINDOW_KEYS = (
    "source",
    "profile",
    "backfill_start_ms",
    "backfill_end_ms",
    "triggered_at_ms",
)


@funclogger
def _noop_progress(_payload: dict[str, object]) -> None:
    return None


def _queue_job_event(
    queue: Queue[object],
    event: str,
    job: str,
    payload: dict[str, object],
) -> None:
    payload["job"] = job
    payload["job_id"] = job
    queue.put((event, payload))


def _queue_job_complete(
    queue: Queue[object],
    job: str,
    message: str,
    result: dict[str, object] | None = None,
) -> None:
    payload: dict[str, object] = {
        "step": "complete",
        "message": message,
    }
    if result is not None:
        payload["result"] = result
    _queue_job_event(queue, "complete", job, payload)


def _queue_job_error(queue: Queue[object], job: str, message: str) -> None:
    _queue_job_event(
        queue,
        "error",
        job,
        {
            "step": "error",
            "message": message,
        },
    )


def _queue_progress(
    queue: Queue[object],
    job: str,
    step: str,
    message: str | None = None,
    extra: dict[str, object] | None = None,
) -> None:
    payload: dict[str, object] = {
        "job": job,
        "step": step,
        "timestamp": int(time_module.time()),
    }
    if message:
        payload["message"] = message
    if extra:
        payload.update(extra)
    queue.put(("progress", payload))


def _queue_backfill_window(
    queue: Queue[object],
    job: str,
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
    triggered_at_ms: int,
) -> None:
    if backfill_start_ms is None and backfill_end_ms is None:
        return
    _queue_progress(
        queue,
        job,
        "backfill_window",
        message="Backfill window resolved",
        extra={
            "backfill_start_ms": backfill_start_ms,
            "backfill_end_ms": backfill_end_ms,
            "triggered_at_ms": triggered_at_ms,
        },
    )


def _resolve_backfill_window(
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
) -> tuple[int, int | None]:
    triggered_at_ms = int(time_module.time() * 1000)
    effective_end_ms = _resolve_backfill_end_ms(
        backfill_start_ms,
        backfill_end_ms,
        triggered_at_ms,
    )
    return triggered_at_ms, effective_end_ms


def _event_stream(queue: Queue[object], sentinel: object) -> Iterator[bytes]:
    yield b"retry: 1000\n\n"
    while True:
        try:
            item = queue.get(timeout=1)
        except Empty:
            yield b": keep-alive\n\n"
            continue
        if item is sentinel:
            break
        event, payload = cast(tuple[str, dict[str, object]], item)
        yield _format_sse(event, payload)


def _streaming_response(queue: Queue[object], sentinel: object) -> StreamingResponse:
    """Return a streaming response for the job event stream."""
    return StreamingResponse(
        _event_stream(queue, sentinel),
        media_type="text/event-stream",
    )


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
        window=BackfillWindow(
            source=request.source,
            profile=request.profile,
            backfill_start_ms=request.backfill_start_ms,
            backfill_end_ms=request.backfill_end_ms,
            triggered_at_ms=triggered_at_ms,
        ),
        progress=progress,
    )


def _run_airflow_daily_sync_job(
    context: AirflowDailySyncContext,
) -> dict[str, object]:
    """Trigger an Airflow daily sync run and report progress."""
    _queue_progress(
        context.queue,
        context.job,
        "start",
        message="Starting Airflow daily_game_sync",
    )
    _queue_backfill_window(
        context.queue,
        context.job,
        context.backfill_start_ms,
        context.backfill_end_ms,
        context.triggered_at_ms,
    )
    run_id = _trigger_airflow_daily_sync(
        context.settings,
        context.source,
        context.profile,
        backfill_start_ms=context.backfill_start_ms,
        backfill_end_ms=context.backfill_end_ms,
        triggered_at_ms=context.triggered_at_ms,
    )
    _queue_progress(
        context.queue,
        context.job,
        "airflow_triggered",
        message="Airflow DAG triggered",
        extra={"run_id": run_id},
    )
    state = _wait_for_airflow_run(context.settings, context.queue, context.job, run_id)
    _ensure_airflow_success(state)
    payload = get_dashboard_payload(
        DashboardQuery(source=context.source),
        get_settings(source=context.source),
    )
    _queue_progress(
        context.queue,
        context.job,
        "fetch_games",
        message="Airflow DAG completed game ingestion",
    )
    _queue_progress(
        context.queue,
        context.job,
        "raw_pgns",
        message="Airflow DAG completed raw PGN fetch",
    )
    _queue_progress(
        context.queue,
        context.job,
        "raw_pgns_persisted",
        message="Airflow DAG persisted raw PGNs",
    )
    _queue_progress(
        context.queue,
        context.job,
        "extract_positions",
        message="Airflow DAG extracted positions",
    )
    _queue_progress(
        context.queue,
        context.job,
        "positions_ready",
        message="Airflow DAG stored positions",
    )
    _queue_progress(
        context.queue,
        context.job,
        "analyze_positions",
        message="Airflow DAG analyzed tactics",
    )
    _queue_progress(
        context.queue,
        context.job,
        "metrics_refreshed",
        message="Airflow DAG refreshed metrics",
        extra={"metrics_version": payload.get("metrics_version")},
    )
    logger.info(
        "Airflow daily_game_sync completed; metrics_version=%s",
        payload.get("metrics_version"),
    )
    return {
        "airflow_run_id": run_id,
        "state": state,
        "metrics_version": payload.get("metrics_version"),
    }


def _wait_for_airflow_run(
    settings: Settings,
    queue: Queue[object],
    job: str,
    run_id: str,
) -> str:
    start = time_module.time()
    last_state: str | None = None
    while True:
        state = _airflow_state(settings, run_id)
        if state != last_state:
            _queue_progress(
                queue,
                job,
                "airflow_state",
                message=state,
                extra={"state": state, "run_id": run_id},
            )
            last_state = state
        if state in {"success", "failed"}:
            return state
        if time_module.time() - start > settings.airflow_poll_timeout_s:
            raise TimeoutError("Airflow run timed out")
        time_module.sleep(settings.airflow_poll_interval_s)


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
                    window=ctx.window,
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


def _stream_job_worker(
    context: StreamJobWorkerContext,
) -> None:
    def progress(payload: dict[str, object]) -> None:
        _queue_job_event(context.queue, "progress", context.job, payload)

    try:
        result = _run_stream_job(
            StreamJobRunContext(
                settings=context.settings,
                queue=context.queue,
                job=context.job,
                window=context.window,
                progress=progress,
            )
        )
        if context.job in {"daily_game_sync", "refresh_metrics"}:
            _refresh_dashboard_cache_async(_sources_for_cache_refresh(context.source))
        _queue_job_complete(context.queue, context.job, "Job complete", result=result)
    except Exception as exc:  # pragma: no cover - defensive
        _queue_job_error(context.queue, context.job, str(exc))
    finally:
        context.queue.put(context.sentinel)


def _stream_job_response(
    request: StreamJobRequest,
    *,
    settings_factory: Callable[..., Settings] = get_settings,
) -> StreamingResponse:
    normalized_source = _normalize_source(request.source)
    settings = settings_factory(source=normalized_source, profile=request.profile)
    queue: Queue[object] = Queue()
    sentinel = object()
    triggered_at_ms, effective_end_ms = _resolve_backfill_window(
        request.backfill_start_ms,
        request.backfill_end_ms,
    )
    Thread(
        target=_stream_job_worker,
        args=(
            StreamJobWorkerContext(
                settings=settings,
                queue=queue,
                sentinel=sentinel,
                job=request.job,
                window=BackfillWindow(
                    source=normalized_source,
                    profile=request.profile,
                    backfill_start_ms=request.backfill_start_ms,
                    backfill_end_ms=effective_end_ms,
                    triggered_at_ms=triggered_at_ms,
                ),
            ),
        ),
        daemon=True,
    ).start()

    return _streaming_response(queue, sentinel)


@funclogger
def stream_jobs(  # pragma: no cover
    job: Annotated[str, Query()] = "daily_game_sync",
    source: Annotated[str | None, Query()] = None,
    profile: Annotated[str | None, Query()] = None,
    backfill_start_ms: Annotated[int | None, Query(ge=0)] = None,
    backfill_end_ms: Annotated[int | None, Query(ge=0)] = None,
) -> StreamingResponse:
    """Stream job events for the requested background task."""
    return _stream_job_response(
        StreamJobRequest(job, source, profile, backfill_start_ms, backfill_end_ms),
        settings_factory=get_settings,
    )


def stream_job_by_id(
    job_id: str,
    source: Annotated[str | None, Query()] = None,
    profile: Annotated[str | None, Query()] = None,
    backfill_start_ms: Annotated[int | None, Query(ge=0)] = None,
    backfill_end_ms: Annotated[int | None, Query(ge=0)] = None,
) -> StreamingResponse:
    """Return a streaming response for the requested job id."""
    return _stream_job_response(
        StreamJobRequest(
            job=job_id,
            source=source,
            profile=profile,
            backfill_start_ms=backfill_start_ms,
            backfill_end_ms=backfill_end_ms,
        )
    )


def _stream_metrics_worker(  # pragma: no cover
    context: MetricsStreamContext,
) -> None:
    """Run metrics refresh and emit streaming job events."""

    def progress(payload: dict[str, object]) -> None:
        _queue_job_event(context.queue, "progress", "refresh_metrics", payload)

    try:
        result = run_refresh_metrics(
            context.settings,
            source=context.normalized_source,
            progress=progress,
        )
        _refresh_dashboard_cache_async(_sources_for_cache_refresh(context.normalized_source))
        payload = get_dashboard_payload(
            DashboardQuery(
                source=context.normalized_source,
                motif=context.motif,
                rating_bucket=context.rating_bucket,
                time_control=context.time_control,
                start_date=context.start_date,
                end_date=context.end_date,
            ),
            context.settings,
        )
        metrics_payload = jsonable_encoder(
            {
                "step": "metrics_update",
                "job": "refresh_metrics",
                "job_id": "refresh_metrics",
                "source": payload.get("source"),
                "metrics_version": payload.get("metrics_version"),
                "metrics": payload.get("metrics"),
            }
        )
        _queue_job_event(context.queue, "metrics_update", "refresh_metrics", metrics_payload)
        _queue_job_complete(
            context.queue,
            "refresh_metrics",
            "Metrics refresh complete",
            result=result,
        )
    except Exception as exc:  # pragma: no cover - defensive
        _queue_job_error(context.queue, "refresh_metrics", str(exc))
    finally:
        context.queue.put(context.sentinel)


def stream_metrics(
    filters: Annotated[DashboardQueryFilters, Depends()],
    motif: Annotated[str | None, Query()] = None,
) -> StreamingResponse:
    """Stream metrics updates based on dashboard filters."""
    start_datetime, end_datetime, normalized_source, settings = _resolve_dashboard_filters(
        filters,
    )
    queue: Queue[object] = Queue()
    sentinel = object()
    context = MetricsStreamContext(
        queue=queue,
        sentinel=sentinel,
        settings=settings,
        filters=MetricsFilters(
            normalized_source=normalized_source,
            motif=motif,
            rating_bucket=filters.rating_bucket,
            time_control=filters.time_control,
            start_date=start_datetime,
            end_date=end_datetime,
        ),
    )

    Thread(
        target=_stream_metrics_worker,
        args=(context,),
        daemon=True,
    ).start()

    return StreamingResponse(
        _event_stream(queue, sentinel),
        media_type="text/event-stream",
    )


_VULTURE_USED = (build_stream_job_request,)

__all__ = [
    "BACKFILL_WINDOW_KEYS",
    "AirflowDailySyncContext",
    "AirflowDailySyncTriggerContext",
    "MetricsStreamContext",
    "StreamJobRequest",
    "StreamJobRunContext",
    "StreamJobWorkerContext",
    "_event_stream",
    "_queue_backfill_window",
    "_queue_job_complete",
    "_queue_job_error",
    "_queue_job_event",
    "_queue_progress",
    "_resolve_backfill_window",
    "_run_airflow_daily_sync_job",
    "_run_stream_job",
    "_stream_job_response",
    "_stream_job_worker",
    "_stream_metrics_worker",
    "_streaming_response",
    "_wait_for_airflow_run",
    "build_stream_job_kwargs",
    "build_stream_job_request",
    "build_stream_job_request_from_values",
    "stream_job_by_id",
    "stream_jobs",
    "stream_metrics",
]
