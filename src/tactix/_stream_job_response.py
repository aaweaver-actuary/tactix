from collections.abc import Callable
from queue import Queue
from threading import Thread

from fastapi.responses import StreamingResponse

from tactix.config import Settings
from tactix.config import get_settings as default_get_settings
from tactix.normalize_source__source import _normalize_source
from tactix.resolve_backfill_window__job_stream import _resolve_backfill_window
from tactix.stream_job_context import StreamJobRequest, StreamJobWorkerContext
from tactix.stream_job_worker__job_stream import _stream_job_worker
from tactix.streaming_response__job_stream import _streaming_response


def _stream_job_response(
    request: StreamJobRequest,
    *,
    get_settings: Callable[..., Settings] = default_get_settings,
) -> StreamingResponse:
    normalized_source = _normalize_source(request.source)
    settings = get_settings(source=normalized_source, profile=request.profile)
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
                source=normalized_source,
                profile=request.profile,
                backfill_start_ms=request.backfill_start_ms,
                backfill_end_ms=effective_end_ms,
                triggered_at_ms=triggered_at_ms,
            ),
        ),
        daemon=True,
    ).start()

    return _streaming_response(queue, sentinel)
