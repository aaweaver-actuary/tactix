from __future__ import annotations

from queue import Queue

from tactix.api_logger__tactix import logger
from tactix.config import Settings, get_settings
from tactix.ensure_airflow_success__airflow_jobs import _ensure_airflow_success
from tactix.pipeline import get_dashboard_payload
from tactix.queue_backfill_window__job_stream import _queue_backfill_window
from tactix.queue_progress__job_stream import _queue_progress
from tactix.trigger_airflow_daily_sync__airflow_jobs import _trigger_airflow_daily_sync
from tactix.wait_for_airflow_run__job_stream import _wait_for_airflow_run


def _run_airflow_daily_sync_job(
    settings: Settings,
    queue: Queue[object],
    job: str,
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
    triggered_at_ms: int,
) -> dict[str, object]:
    _queue_progress(
        queue,
        job,
        "start",
        message="Starting Airflow daily_game_sync",
    )
    _queue_backfill_window(
        queue,
        job,
        backfill_start_ms,
        backfill_end_ms,
        triggered_at_ms,
    )
    run_id = _trigger_airflow_daily_sync(
        settings,
        source,
        profile,
        backfill_start_ms=backfill_start_ms,
        backfill_end_ms=backfill_end_ms,
        triggered_at_ms=triggered_at_ms,
    )
    _queue_progress(
        queue,
        job,
        "airflow_triggered",
        message="Airflow DAG triggered",
        extra={"run_id": run_id},
    )
    state = _wait_for_airflow_run(settings, queue, job, run_id)
    _ensure_airflow_success(state)
    payload = get_dashboard_payload(
        get_settings(source=source),
        source=source,
    )
    _queue_progress(
        queue,
        job,
        "fetch_games",
        message="Airflow DAG completed game ingestion",
    )
    _queue_progress(
        queue,
        job,
        "raw_pgns",
        message="Airflow DAG completed raw PGN fetch",
    )
    _queue_progress(
        queue,
        job,
        "raw_pgns_persisted",
        message="Airflow DAG persisted raw PGNs",
    )
    _queue_progress(
        queue,
        job,
        "extract_positions",
        message="Airflow DAG extracted positions",
    )
    _queue_progress(
        queue,
        job,
        "positions_ready",
        message="Airflow DAG stored positions",
    )
    _queue_progress(
        queue,
        job,
        "analyze_positions",
        message="Airflow DAG analyzed tactics",
    )
    _queue_progress(
        queue,
        job,
        "metrics_refreshed",
        message="Airflow DAG refreshed metrics",
        extra={"metrics_version": payload.get("metrics_version")},
    )
    logger.info(
        "Airflow daily_game_sync completed; metrics_version=%s",
        payload.get("metrics_version"),
    )
    return {
        "airflow_run_id": run_id,
        "state": state,
        "metrics_version": payload.get("metrics_version"),
    }
