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
