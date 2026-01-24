import json

from fastapi.testclient import TestClient

from tactix.api import app
from tactix.config import get_settings


def test_job_stream_emits_progress_and_complete():
    client = TestClient(app)
    token = get_settings().api_token
    headers = {"Authorization": f"Bearer {token}"}
    events: list[tuple[str, dict[str, object]]] = []

    with client.stream(
        "GET",
        "/api/jobs/stream?job=refresh_metrics&source=lichess",
        headers=headers,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

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

    event_names = {name for name, _ in events}
    assert "progress" in event_names
    assert "complete" in event_names
    assert any(
        name == "progress" and data.get("step") in {"start", "metrics_refreshed"}
        for name, data in events
    )
