from unittest.mock import patch

from fastapi.testclient import TestClient

from tactix.api import app
from tactix.config import get_settings


def test_refresh_metrics_job_triggers_cache_refresh() -> None:
    client = TestClient(app)
    token = get_settings().api_token

    with (
        patch("tactix.trigger_refresh_metrics__api_jobs.run_refresh_metrics", return_value={"status": "ok"}) as run_job,
        patch("tactix.trigger_refresh_metrics__api_jobs._sources_for_cache_refresh", return_value=["lichess"]) as sources,
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


def test_migrations_job_skips_cache_refresh() -> None:
    client = TestClient(app)
    token = get_settings().api_token

    with (
        patch("tactix.trigger_migrations__api_jobs.run_migrations", return_value={"status": "ok"}) as run_job,
        patch("tactix.refresh_dashboard_cache_async__api_cache._refresh_dashboard_cache_async") as refresh,
    ):
        response = client.post(
            "/api/jobs/migrations?source=lichess",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["result"] == {"status": "ok"}
    run_job.assert_called_once()
    refresh.assert_not_called()
