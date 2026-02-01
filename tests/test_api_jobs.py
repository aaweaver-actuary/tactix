from unittest.mock import patch

from fastapi.testclient import TestClient

from tactix.api import app
from tactix.config import get_settings


def test_refresh_metrics_job_triggers_cache_refresh() -> None:
    client = TestClient(app)
    token = get_settings().api_token

    with (
        patch(
            "tactix.trigger_refresh_metrics__api_jobs.run_refresh_metrics",
            return_value={"status": "ok"},
        ) as run_job,
        patch(
            "tactix.trigger_refresh_metrics__api_jobs._sources_for_cache_refresh",
            return_value=["lichess"],
        ) as sources,
        patch("tactix.trigger_refresh_metrics__api_jobs._refresh_dashboard_cache_async") as refresh,
    ):
        response = client.post(
            "/api/jobs/refresh_metrics?source=lichess",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["result"] == {"status": "ok"}
    run_job.assert_called_once()
    sources.assert_called_once_with("lichess")
    refresh.assert_called_once_with(["lichess"])


def test_trigger_job_requires_auth() -> None:
    client = TestClient(app)
    response = client.post("/api/jobs/trigger?job=refresh_metrics")
    assert response.status_code == 401


def test_job_status_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/jobs/refresh_metrics")
    assert response.status_code == 401


def test_job_status_returns_schema() -> None:
    client = TestClient(app)
    token = get_settings().api_token

    with patch("tactix.get_job_status__api_jobs.time_module.time", return_value=2.0):
        response = client.get(
            "/api/jobs/refresh_metrics?source=lichess&backfill_start_ms=1000&backfill_end_ms=2000",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "status",
        "job",
        "job_id",
        "source",
        "profile",
        "backfill_start_ms",
        "backfill_end_ms",
        "requested_at_ms",
        "airflow_enabled",
    }
    assert payload["status"] == "ok"
    assert payload["job"] == "refresh_metrics"
    assert payload["job_id"] == "refresh_metrics"
    assert payload["source"] == "lichess"
    assert payload["profile"] is None
    assert payload["backfill_start_ms"] == 1000
    assert payload["backfill_end_ms"] == 2000
    assert payload["requested_at_ms"] == 2000
    assert isinstance(payload["airflow_enabled"], bool)


def test_trigger_job_returns_schema_and_refreshes_cache() -> None:
    client = TestClient(app)
    token = get_settings().api_token

    with (
        patch("tactix.trigger_job__api_jobs.time_module.time", return_value=1.0),
        patch(
            "tactix.trigger_job__api_jobs._run_stream_job",
            return_value={"status": "ok", "metrics_version": 10},
        ) as run_job,
        patch(
            "tactix.trigger_job__api_jobs._resolve_backfill_end_ms",
            return_value=2000,
        ) as resolve_end,
        patch(
            "tactix.trigger_job__api_jobs._sources_for_cache_refresh",
            return_value=["lichess"],
        ) as sources,
        patch("tactix.trigger_job__api_jobs._refresh_dashboard_cache_async") as refresh,
    ):
        response = client.post(
            "/api/jobs/trigger?job=refresh_metrics&source=lichess&backfill_start_ms=1000",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"status", "job", "result"}
    assert payload["status"] == "ok"
    assert payload["job"] == "refresh_metrics"
    assert payload["result"] == {"status": "ok", "metrics_version": 10}

    resolve_end.assert_called_once_with(1000, None, 1000)
    run_job.assert_called_once()
    sources.assert_called_once_with("lichess")
    refresh.assert_called_once_with(["lichess"])


def test_trigger_job_skips_cache_refresh_for_migrations() -> None:
    client = TestClient(app)
    token = get_settings().api_token

    with (
        patch("tactix.trigger_job__api_jobs.time_module.time", return_value=2.0),
        patch(
            "tactix.trigger_job__api_jobs._run_stream_job",
            return_value={"status": "ok"},
        ) as run_job,
        patch(
            "tactix.trigger_job__api_jobs._resolve_backfill_end_ms",
            return_value=4000,
        ) as resolve_end,
        patch("tactix.trigger_job__api_jobs._refresh_dashboard_cache_async") as refresh,
    ):
        response = client.post(
            "/api/jobs/trigger?job=migrations&source=lichess&backfill_start_ms=3000&backfill_end_ms=3500",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"] == "migrations"
    assert payload["result"] == {"status": "ok"}
    resolve_end.assert_called_once_with(3000, 3500, 2000)
    run_job.assert_called_once()
    refresh.assert_not_called()


def test_migrations_job_skips_cache_refresh() -> None:
    client = TestClient(app)
    token = get_settings().api_token

    with (
        patch(
            "tactix.trigger_migrations__api_jobs.run_migrations", return_value={"status": "ok"}
        ) as run_job,
        patch(
            "tactix.refresh_dashboard_cache_async__api_cache._refresh_dashboard_cache_async"
        ) as refresh,
    ):
        response = client.post(
            "/api/jobs/migrations?source=lichess",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["result"] == {"status": "ok"}
    run_job.assert_called_once()
    refresh.assert_not_called()
