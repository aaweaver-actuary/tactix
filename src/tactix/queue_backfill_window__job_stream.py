from __future__ import annotations

from queue import Queue

from tactix.queue_progress__job_stream import _queue_progress


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
