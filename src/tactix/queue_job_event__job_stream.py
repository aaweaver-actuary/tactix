from __future__ import annotations

from queue import Queue


def _queue_job_event(
    queue: Queue[object],
    event: str,
    job: str,
    payload: dict[str, object],
) -> None:
    payload["job"] = job
    payload["job_id"] = job
    queue.put((event, payload))
