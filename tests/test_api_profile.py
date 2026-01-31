from unittest.mock import patch

from fastapi.testclient import TestClient

from tactix.api import app
from tactix.config import get_settings


def test_daily_game_sync_accepts_profile_param() -> None:
    client = TestClient(app)
    token = get_settings().api_token

    with patch("tactix.trigger_daily_sync__api_jobs.run_daily_game_sync") as run_sync:
        run_sync.return_value = {"status": "ok"}
        response = client.post(
            "/api/jobs/daily_game_sync?source=lichess&profile=bullet",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert run_sync.call_count == 1
    _, kwargs = run_sync.call_args
    assert kwargs.get("profile") == "bullet"


def test_daily_game_sync_accepts_backfill_window_and_profile() -> None:
    client = TestClient(app)
    token = get_settings().api_token

    with patch("tactix.trigger_daily_sync__api_jobs.run_daily_game_sync") as run_sync:
        run_sync.return_value = {"status": "ok"}
        response = client.post(
            "/api/jobs/daily_game_sync?source=lichess&profile=bullet&backfill_start_ms=10&backfill_end_ms=20",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert run_sync.call_count == 1
    _, kwargs = run_sync.call_args
    assert kwargs.get("profile") == "bullet"
    assert kwargs.get("window_start_ms") == 10
    assert kwargs.get("window_end_ms") == 20


def test_refresh_metrics_triggers_cache_refresh() -> None:
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
