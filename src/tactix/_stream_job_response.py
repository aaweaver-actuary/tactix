import time as time_module
from collections.abc import Callable
from queue import Queue
from threading import Thread

from fastapi.responses import StreamingResponse

from tactix.config import Settings
from tactix.config import get_settings as default_get_settings
from tactix.event_stream__job_stream import _event_stream
from tactix.normalize_source__source import _normalize_source
from tactix.resolve_backfill_end_ms__airflow_jobs import _resolve_backfill_end_ms
from tactix.stream_job_worker__job_stream import _stream_job_worker


def _stream_job_response(
    job_id: str,
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
    *,
    get_settings: Callable[..., Settings] = default_get_settings,
) -> StreamingResponse:
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source, profile=profile)
    queue: Queue[object] = Queue()
    sentinel = object()
    triggered_at_ms = int(time_module.time() * 1000)
    effective_end_ms = _resolve_backfill_end_ms(
        backfill_start_ms,
        backfill_end_ms,
        triggered_at_ms,
    )
    Thread(
        target=_stream_job_worker,
        args=(
            settings,
            queue,
            sentinel,
            job_id,
            normalized_source,
            profile,
            backfill_start_ms,
            effective_end_ms,
            triggered_at_ms,
        ),
        daemon=True,
    ).start()

    return StreamingResponse(
        _event_stream(queue, sentinel),
        media_type="text/event-stream",
    )
