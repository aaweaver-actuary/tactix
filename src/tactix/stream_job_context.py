"""Context objects for stream job processing."""

# pylint: disable=too-many-instance-attributes

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from queue import Queue

from tactix.config import Settings


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
