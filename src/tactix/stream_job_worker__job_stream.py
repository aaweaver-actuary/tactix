from __future__ import annotations

from queue import Queue

from tactix.config import Settings
from tactix.list_sources_for_cache_refresh__api_cache import _sources_for_cache_refresh
from tactix.queue_job_event__job_stream import _queue_job_event
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async
from tactix.run_stream_job__job_stream import _run_stream_job


def _stream_job_worker(
    settings: Settings,
    queue: Queue[object],
    sentinel: object,
    job: str,
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
    triggered_at_ms: int,
) -> None:
    def progress(payload: dict[str, object]) -> None:
        _queue_job_event(queue, "progress", job, payload)

    try:
        result = _run_stream_job(
            settings,
            queue,
            job,
            source,
            profile,
            backfill_start_ms,
            backfill_end_ms,
            triggered_at_ms,
            progress,
        )
        if job in {"daily_game_sync", "refresh_metrics"}:
            _refresh_dashboard_cache_async(_sources_for_cache_refresh(source))
        _queue_job_event(
            queue,
            "complete",
            job,
            {
                "step": "complete",
                "message": "Job complete",
                "result": result,
            },
        )
    except Exception as exc:  # pragma: no cover - defensive
        _queue_job_event(
            queue,
            "error",
            job,
            {
                "step": "error",
                "message": str(exc),
            },
        )
    finally:
        queue.put(sentinel)
