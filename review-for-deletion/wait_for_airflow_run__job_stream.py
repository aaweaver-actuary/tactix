from __future__ import annotations

import time as time_module
from queue import Queue

from tactix.get_airflow_state__airflow_jobs import _airflow_state
from tactix.queue_progress__job_stream import _queue_progress


def _wait_for_airflow_run(
    settings,
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
