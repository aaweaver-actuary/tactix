import json
from unittest.mock import ANY, patch

from fastapi.testclient import TestClient

from tactix.api import app
from tactix.config import Settings, get_settings


def _stream_events(client: TestClient, url: str, token: str) -> list[tuple[str, dict[str, object]]]:
    headers = {"Authorization": f"Bearer {token}"}
    events: list[tuple[str, dict[str, object]]] = []
    with client.stream("GET", url, headers=headers) as response:
        assert response.status_code == 200
        current_event = None
        current_data = None
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if line.startswith(":"):
                continue
            if line.startswith("event: "):
                current_event = line.replace("event: ", "", 1).strip()
                continue
            if line.startswith("data: "):
                current_data = json.loads(line.replace("data: ", "", 1))
            if current_event and current_data is not None:
                events.append((current_event, current_data))
                if current_event == "complete":
                    break
                current_event = None
                current_data = None
    return events


def _assert_progress_schema(payload: dict[str, object], job_id: str) -> None:
    assert payload.get("job") == job_id
    assert payload.get("job_id") == job_id
    assert isinstance(payload.get("step"), str)
    assert "timestamp" in payload


def _assert_complete_schema(payload: dict[str, object], job_id: str) -> None:
    assert payload.get("job") == job_id
    assert payload.get("job_id") == job_id
    assert payload.get("step") == "complete"
    assert isinstance(payload.get("message"), str)
    assert isinstance(payload.get("result"), dict)


def test_job_stream_emits_progress_and_complete():
    client = TestClient(app)
    token = get_settings().api_token
    events: list[tuple[str, dict[str, object]]] = []
    events = _stream_events(
        client,
        "/api/jobs/stream?job=refresh_metrics&source=lichess",
        token,
    )

    event_names = {name for name, _ in events}
    assert "progress" in event_names
    assert "complete" in event_names
    assert any(
        name == "progress" and data.get("step") in {"start", "metrics_refreshed"}
        for name, data in events
    )


def test_job_stream_by_id_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/jobs/refresh_metrics/stream")
    assert response.status_code == 401


def test_job_stream_by_id_returns_schema() -> None:
    client = TestClient(app)
    token = get_settings().api_token

    events = _stream_events(
        client,
        "/api/jobs/refresh_metrics/stream?source=lichess",
        token,
    )

    progress_payloads = [data for name, data in events if name == "progress"]
    complete_payloads = [data for name, data in events if name == "complete"]

    assert progress_payloads
    assert complete_payloads
    _assert_progress_schema(progress_payloads[0], "refresh_metrics")
    _assert_complete_schema(complete_payloads[-1], "refresh_metrics")


def test_daily_game_sync_stream_uses_airflow_when_enabled() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    settings = Settings()
    settings.airflow_enabled = True
    settings.airflow_base_url = "http://airflow"
    settings.airflow_username = "admin"
    settings.airflow_password = "admin"
    with (
        patch("tactix.stream_jobs__api.get_settings", return_value=settings),
        patch(
            "tactix.run_airflow_daily_sync_job__job_stream._trigger_airflow_daily_sync",
            return_value="run-1",
        ) as trigger,
        patch(
            "tactix.run_airflow_daily_sync_job__job_stream._wait_for_airflow_run",
            return_value="success",
        ),
        patch(
            "tactix.run_airflow_daily_sync_job__job_stream.get_dashboard_payload",
            return_value={"metrics_version": 12},
        ),
    ):
        events = _stream_events(
            client,
            "/api/jobs/stream?job=daily_game_sync&source=lichess&backfill_start_ms=100&backfill_end_ms=200",
            token,
        )

    trigger.assert_called_once_with(
        settings,
        "lichess",
        None,
        backfill_start_ms=100,
        backfill_end_ms=200,
        triggered_at_ms=ANY,
    )
    assert any(name == "progress" for name, _ in events)
    assert any(name == "complete" for name, _ in events)
