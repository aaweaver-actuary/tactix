from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from tactix.api import app
from tactix.app.use_cases.postgres import get_postgres_use_case
from tactix.config import get_settings


def test_postgres_status_disabled(monkeypatch) -> None:
    monkeypatch.delenv("TACTIX_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("TACTIX_POSTGRES_HOST", raising=False)
    monkeypatch.delenv("TACTIX_POSTGRES_DB", raising=False)
    monkeypatch.delenv("TACTIX_POSTGRES_USER", raising=False)
    monkeypatch.delenv("TACTIX_POSTGRES_PASSWORD", raising=False)

    client = TestClient(app)
    token = get_settings().api_token
    response = client.get("/api/postgres/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["status"] == "disabled"
    assert payload["events"] == []


def test_postgres_raw_pgns_endpoint_returns_summary() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    payload = {
        "status": "ok",
        "total_rows": 5,
        "distinct_games": 3,
        "latest_ingested_at": "2026-01-27T00:00:00Z",
        "sources": [
            {
                "source": "lichess",
                "total_rows": 5,
                "distinct_games": 3,
                "latest_ingested_at": "2026-01-27T00:00:00Z",
            }
        ],
    }

    use_case = MagicMock()
    use_case.get_raw_pgns.return_value = payload
    app.dependency_overrides[get_postgres_use_case] = lambda: use_case
    try:
        response = client.get(
            "/api/postgres/raw_pgns",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides = {}

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["total_rows"] == 5


def test_postgres_analysis_endpoint_returns_rows() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    use_case = MagicMock()
    use_case.get_analysis.return_value = {
        "status": "ok",
        "tactics": [{"tactic_id": 1, "motif": "fork"}],
    }
    app.dependency_overrides[get_postgres_use_case] = lambda: use_case
    try:
        response = client.get(
            "/api/postgres/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides = {}

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["tactics"][0]["tactic_id"] == 1


def test_postgres_status_endpoint_returns_payload() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    use_case = MagicMock()
    use_case.get_status.return_value = {
        "enabled": True,
        "status": "ok",
        "latency_ms": 1.0,
        "error": None,
        "schema": "tactix_ops",
        "tables": ["tactix_ops.ops_events"],
        "events": [],
    }
    app.dependency_overrides[get_postgres_use_case] = lambda: use_case
    try:
        response = client.get(
            "/api/postgres/status",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides = {}

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["tables"] == ["tactix_ops.ops_events"]
