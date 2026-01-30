from __future__ import annotations

import time as time_module
from queue import Queue


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
