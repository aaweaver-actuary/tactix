from datetime import datetime

from fastapi.testclient import TestClient

from tactix.api import app
from tactix.config import get_settings


# API auth tests


def test_health_is_unauthenticated():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_schema_with_auth() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    response = client.get("/api/health", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"status", "service", "version", "timestamp"}
    assert payload["status"] == "ok"
    assert payload["service"] == "tactix"
    assert isinstance(payload["version"], str)
    assert isinstance(payload["timestamp"], str)
    datetime.fromisoformat(payload["timestamp"])


def test_requires_auth_for_dashboard():
    client = TestClient(app)
    response = client.get("/api/dashboard")
    assert response.status_code == 401


def test_allows_authorization_header():
    client = TestClient(app)
    token = get_settings().api_token
    response = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_allows_api_key_header():
    client = TestClient(app)
    token = get_settings().api_token
    response = client.get("/api/practice/queue", headers={"X-API-Key": token})
    assert response.status_code == 200


def test_raw_pgns_summary_allows_token():
    client = TestClient(app)
    token = get_settings().api_token
    response = client.get("/api/raw_pgns/summary", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    response = client.get("/api/stats/motifs")
    assert response.status_code == 401


def test_stats_motifs_returns_schema():
    client = TestClient(app)
    token = get_settings().api_token
    response = client.get(
        "/api/stats/motifs?source=all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"source", "metrics_version", "motifs"}
    assert payload["source"] == "all"
    assert isinstance(payload["metrics_version"], int)
    assert isinstance(payload["motifs"], list)

    if not payload["motifs"]:
        return

    row = payload["motifs"][0]
    required_keys = {
        "source",
        "metric_type",
        "motif",
        "window_days",
        "trend_date",
        "rating_bucket",
        "time_control",
        "total",
        "found",
        "missed",
        "failed_attempt",
        "unclear",
        "found_rate",
        "miss_rate",
        "updated_at",
    }
    assert required_keys.issubset(row.keys())
    assert row["metric_type"] == "motif_breakdown"
    assert isinstance(row["total"], int)
    assert isinstance(row["found"], int)
    assert isinstance(row["missed"], int)
    assert isinstance(row["failed_attempt"], int)
    assert isinstance(row["unclear"], int)
    assert row["found_rate"] is None or isinstance(row["found_rate"], (int, float))
    assert row["miss_rate"] is None or isinstance(row["miss_rate"], (int, float))
