from fastapi.testclient import TestClient
from unittest.mock import patch

from tactix.api import app
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

    with patch(
        "tactix.get_postgres_raw_pgns__api.PostgresRepository.fetch_raw_pgns_summary",
        return_value=payload,
    ):
        response = client.get(
            "/api/postgres/raw_pgns",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["total_rows"] == 5


def test_postgres_analysis_endpoint_returns_rows() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    with patch(
        "tactix.get_postgres_analysis__api.PostgresRepository.fetch_analysis_tactics",
        return_value=[{"tactic_id": 1, "motif": "fork"}],
    ):
        response = client.get(
            "/api/postgres/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["tactics"][0]["tactic_id"] == 1


def test_postgres_status_endpoint_returns_payload() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    with (
        patch("tactix.get_postgres_status__api.PostgresRepository.get_status") as get_status,
        patch(
            "tactix.get_postgres_status__api.PostgresRepository.fetch_ops_events", return_value=[]
        ),
    ):
        get_status.return_value = type(
            "MockStatus",
            (),
            {
                "enabled": True,
                "status": "ok",
                "latency_ms": 1.0,
                "error": None,
                "schema": "tactix_ops",
                "tables": ["tactix_ops.ops_events"],
            },
        )()
        response = client.get(
            "/api/postgres/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["tables"] == ["tactix_ops.ops_events"]
