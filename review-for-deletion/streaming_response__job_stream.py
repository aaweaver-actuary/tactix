"""Streaming response helpers for job streams."""

from __future__ import annotations

from queue import Queue

from fastapi.responses import StreamingResponse

from tactix.event_stream__job_stream import _event_stream


def _streaming_response(queue: Queue[object], sentinel: object) -> StreamingResponse:
    """Return a streaming response for the job event stream."""
    return StreamingResponse(
        _event_stream(queue, sentinel),
        media_type="text/event-stream",
    )
