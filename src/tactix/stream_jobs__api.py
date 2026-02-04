"""API endpoint to stream background job events."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query
from fastapi.responses import StreamingResponse

from tactix._stream_job_response import _stream_job_response
from tactix.config import get_settings
from tactix.stream_job_context import StreamJobRequest
from tactix.utils import funclogger


@funclogger
def stream_jobs(
    job: Annotated[str, Query()] = "daily_game_sync",
    source: Annotated[str | None, Query()] = None,
    profile: Annotated[str | None, Query()] = None,
    backfill_start_ms: Annotated[int | None, Query(ge=0)] = None,
    backfill_end_ms: Annotated[int | None, Query(ge=0)] = None,
) -> StreamingResponse:
    """Stream job events for the requested background task."""
    return _stream_job_response(
        StreamJobRequest(job, source, profile, backfill_start_ms, backfill_end_ms),
        get_settings=get_settings,
    )


__all__ = ["get_settings", "stream_jobs"]
