"""Tests for Airflow daily sync job runner."""

from __future__ import annotations

from queue import Queue

from tactix.config import get_settings
from tactix.run_airflow_daily_sync_job__job_stream import _run_airflow_daily_sync_job
from tactix.stream_job_context import AirflowDailySyncContext


def test_run_airflow_daily_sync_job(monkeypatch) -> None:
    events: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_queue_progress(queue, job, phase, message, extra=None):
        events.append((phase, message, extra))

    monkeypatch.setattr(
        "tactix.run_airflow_daily_sync_job__job_stream._queue_progress",
        fake_queue_progress,
    )
    monkeypatch.setattr(
        "tactix.run_airflow_daily_sync_job__job_stream._queue_backfill_window",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "tactix.run_airflow_daily_sync_job__job_stream._trigger_airflow_daily_sync",
        lambda *args, **kwargs: "run-123",
    )
    monkeypatch.setattr(
        "tactix.run_airflow_daily_sync_job__job_stream._wait_for_airflow_run",
        lambda *args, **kwargs: "success",
    )
    monkeypatch.setattr(
        "tactix.run_airflow_daily_sync_job__job_stream._ensure_airflow_success",
        lambda *_: None,
    )
    monkeypatch.setattr(
        "tactix.run_airflow_daily_sync_job__job_stream.get_dashboard_payload",
        lambda *args, **kwargs: {"metrics_version": "v1"},
    )
    monkeypatch.setattr(
        "tactix.run_airflow_daily_sync_job__job_stream.get_settings",
        lambda **kwargs: get_settings(),
    )

    ctx = AirflowDailySyncContext(
        settings=get_settings(),
        queue=Queue(),
        job="daily_game_sync",
        source=None,
        profile=None,
        backfill_start_ms=None,
        backfill_end_ms=None,
        triggered_at_ms=123,
    )

    result = _run_airflow_daily_sync_job(ctx)
    assert result["airflow_run_id"] == "run-123"
    assert result["state"] == "success"
    assert result["metrics_version"] == "v1"
    assert events
