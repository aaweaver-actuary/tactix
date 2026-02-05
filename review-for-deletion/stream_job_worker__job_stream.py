from __future__ import annotations

from tactix.list_sources_for_cache_refresh__api_cache import _sources_for_cache_refresh
from tactix.queue_job_event__job_stream import (
    _queue_job_complete,
    _queue_job_error,
    _queue_job_event,
)
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async
from tactix.run_stream_job__job_stream import _run_stream_job
from tactix.stream_job_context import StreamJobRunContext, StreamJobWorkerContext


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
                source=context.source,
                profile=context.profile,
                backfill_start_ms=context.backfill_start_ms,
                backfill_end_ms=context.backfill_end_ms,
                triggered_at_ms=context.triggered_at_ms,
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
