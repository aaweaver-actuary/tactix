from __future__ import annotations

from datetime import datetime
from queue import Queue
from threading import Thread
from typing import Annotated

from fastapi import Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from tactix.config import Settings
from tactix.event_stream__job_stream import _event_stream
from tactix.get_dashboard__api import DashboardQueryFilters, _resolve_dashboard_filters
from tactix.list_sources_for_cache_refresh__api_cache import _sources_for_cache_refresh
from tactix.pipeline import get_dashboard_payload, run_refresh_metrics
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async


def _stream_metrics_worker(
    queue: Queue[object],
    sentinel: object,
    settings: Settings,
    normalized_source: str | None,
    motif: str | None,
    rating_bucket: str | None,
    time_control: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> None:
    def progress(payload: dict[str, object]) -> None:
        payload["job"] = "refresh_metrics"
        payload["job_id"] = "refresh_metrics"
        queue.put(("progress", payload))

    try:
        result = run_refresh_metrics(settings, source=normalized_source, progress=progress)
        _refresh_dashboard_cache_async(_sources_for_cache_refresh(normalized_source))
        payload = get_dashboard_payload(
            settings,
            source=normalized_source,
            motif=motif,
            rating_bucket=rating_bucket,
            time_control=time_control,
            start_date=start_date,
            end_date=end_date,
        )
        metrics_payload = jsonable_encoder(
            {
                "step": "metrics_update",
                "job": "refresh_metrics",
                "job_id": "refresh_metrics",
                "source": payload.get("source"),
                "metrics_version": payload.get("metrics_version"),
                "metrics": payload.get("metrics"),
            }
        )
        queue.put(("metrics_update", metrics_payload))
        queue.put(
            (
                "complete",
                {
                    "job": "refresh_metrics",
                    "job_id": "refresh_metrics",
                    "step": "complete",
                    "message": "Metrics refresh complete",
                    "result": result,
                },
            )
        )
    except Exception as exc:  # pragma: no cover - defensive
        queue.put(
            (
                "error",
                {
                    "job": "refresh_metrics",
                    "job_id": "refresh_metrics",
                    "step": "error",
                    "message": str(exc),
                },
            )
        )
    finally:
        queue.put(sentinel)


def stream_metrics(
    filters: Annotated[DashboardQueryFilters, Depends()],
    motif: Annotated[str | None, Query()] = None,
) -> StreamingResponse:
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
