"""Context objects for stream job processing."""

# pylint: disable=too-many-instance-attributes

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from queue import Queue
from typing import cast

from tactix.config import Settings
from tactix.utils.logger import funclogger


@dataclass(frozen=True)
class StreamJobRequest:
    """Incoming stream job request parameters."""

    job: str
    source: str | None
    profile: str | None
    backfill_start_ms: int | None
    backfill_end_ms: int | None


@dataclass(frozen=True)
class StreamJobWorkerContext:
    """Context for streaming job worker execution."""

    settings: Settings
    queue: Queue[object]
    sentinel: object
    job: str
    source: str | None
    profile: str | None
    backfill_start_ms: int | None
    backfill_end_ms: int | None
    triggered_at_ms: int


@dataclass(frozen=True)
class StreamJobRunContext:
    """Context for executing a stream job run."""

    settings: Settings
    queue: Queue[object]
    job: str
    source: str | None
    profile: str | None
    backfill_start_ms: int | None
    backfill_end_ms: int | None
    triggered_at_ms: int
    progress: Callable[[dict[str, object]], None]


@dataclass(frozen=True)
class AirflowDailySyncContext:
    """Context for airflow daily sync jobs."""

    settings: Settings
    queue: Queue[object]
    job: str
    source: str | None
    profile: str | None
    backfill_start_ms: int | None
    backfill_end_ms: int | None
    triggered_at_ms: int


@dataclass(frozen=True)
class AirflowDailySyncTriggerContext:
    """Context for triggering airflow daily sync."""

    settings: Settings
    source: str | None
    profile: str | None
    backfill_start_ms: int | None = None
    backfill_end_ms: int | None = None
    triggered_at_ms: int | None = None


@dataclass(frozen=True)
class MetricsStreamContext:
    """Context for streaming metrics results."""

    queue: Queue[object]
    sentinel: object
    settings: Settings
    normalized_source: str | None
    motif: str | None
    rating_bucket: str | None
    time_control: str | None
    start_date: datetime | None
    end_date: datetime | None


@funclogger
def build_stream_job_kwargs(
    *,
    job: str,
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
) -> dict[str, object]:
    """Build a kwargs dict for stream job contexts."""
    return {
        "job": job,
        "source": source,
        "profile": profile,
        "backfill_start_ms": backfill_start_ms,
        "backfill_end_ms": backfill_end_ms,
    }


@funclogger
def build_stream_job_request(
    *,
    job: str,
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
) -> StreamJobRequest:
    """Create a StreamJobRequest from common inputs."""
    return StreamJobRequest(
        **build_stream_job_kwargs(
            job=job,
            source=source,
            profile=profile,
            backfill_start_ms=backfill_start_ms,
            backfill_end_ms=backfill_end_ms,
        )
    )


def build_stream_job_request_from_values(
    values: dict[str, object],
) -> StreamJobRequest:
    """Create a StreamJobRequest from a values mapping."""
    return StreamJobRequest(
        job=cast(str, values["job"]),
        source=cast(str | None, values["source"]),
        profile=cast(str | None, values["profile"]),
        backfill_start_ms=cast(int | None, values["backfill_start_ms"]),
        backfill_end_ms=cast(int | None, values["backfill_end_ms"]),
    )


BACKFILL_WINDOW_KEYS = (
    "source",
    "profile",
    "backfill_start_ms",
    "backfill_end_ms",
    "triggered_at_ms",
)
