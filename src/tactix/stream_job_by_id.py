from typing import Annotated

from fastapi import Query
from fastapi.responses import StreamingResponse

from tactix._stream_job_response import _stream_job_response


def stream_job_by_id(
    job_id: str,
    source: Annotated[str | None, Query()] = None,
    profile: Annotated[str | None, Query()] = None,
    backfill_start_ms: Annotated[int | None, Query(ge=0)] = None,
    backfill_end_ms: Annotated[int | None, Query(ge=0)] = None,
) -> StreamingResponse:
    return _stream_job_response(
        job_id,
        source,
        profile,
        backfill_start_ms,
        backfill_end_ms,
    )
