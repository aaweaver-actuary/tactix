"""API endpoint for streaming metrics updates."""

from queue import Queue
from threading import Thread
from typing import Annotated

from fastapi import Depends, Query
from fastapi.responses import StreamingResponse

from tactix._resolve_dashboard_filters import _resolve_dashboard_filters
from tactix._stream_metrics_worker import _stream_metrics_worker
from tactix.DashboardQueryFilters import DashboardQueryFilters
from tactix.event_stream__job_stream import _event_stream


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

    Thread(
        target=_stream_metrics_worker,
        args=(
            queue,
            sentinel,
            settings,
            normalized_source,
            motif,
            filters.rating_bucket,
            filters.time_control,
            start_datetime,
            end_datetime,
        ),
        daemon=True,
    ).start()

    return StreamingResponse(
        _event_stream(queue, sentinel),
        media_type="text/event-stream",
    )
