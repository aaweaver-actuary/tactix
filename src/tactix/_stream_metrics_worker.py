"""Stream metrics refresh results to job clients."""

# pylint: disable=broad-exception-caught

from fastapi.encoders import jsonable_encoder

from tactix.dashboard_query import DashboardQuery
from tactix.list_sources_for_cache_refresh__api_cache import _sources_for_cache_refresh
from tactix.pipeline import get_dashboard_payload, run_refresh_metrics
from tactix.queue_job_event__job_stream import (
    _queue_job_complete,
    _queue_job_error,
    _queue_job_event,
)
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async
from tactix.stream_job_context import MetricsStreamContext


def _stream_metrics_worker(
    context: MetricsStreamContext,
) -> None:
    """Run metrics refresh and emit streaming job events."""

    def progress(payload: dict[str, object]) -> None:
        _queue_job_event(context.queue, "progress", "refresh_metrics", payload)

    try:
        result = run_refresh_metrics(
            context.settings,
            source=context.normalized_source,
            progress=progress,
        )
        _refresh_dashboard_cache_async(_sources_for_cache_refresh(context.normalized_source))
        payload = get_dashboard_payload(
            DashboardQuery(
                source=context.normalized_source,
                motif=context.motif,
                rating_bucket=context.rating_bucket,
                time_control=context.time_control,
                start_date=context.start_date,
                end_date=context.end_date,
            ),
            context.settings,
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
        _queue_job_event(context.queue, "metrics_update", "refresh_metrics", metrics_payload)
        _queue_job_complete(
            context.queue,
            "refresh_metrics",
            "Metrics refresh complete",
            result=result,
        )
    except Exception as exc:  # pragma: no cover - defensive
        _queue_job_error(context.queue, "refresh_metrics", str(exc))
    finally:
        context.queue.put(context.sentinel)
