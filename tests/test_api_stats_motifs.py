from fastapi.testclient import TestClient

from tactix.api import app
from tactix.config import get_settings
from tactix.tactic_scope import allowed_motif_list


def test_stats_motifs_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/stats/motifs")
    assert response.status_code == 401


def test_stats_motifs_returns_schema() -> None:
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
    assert row["motif"] in allowed_motif_list()
    assert isinstance(row["total"], int)
    assert isinstance(row["found"], int)
    assert isinstance(row["missed"], int)
    assert isinstance(row["failed_attempt"], int)
    assert isinstance(row["unclear"], int)
    assert row["found_rate"] is None or isinstance(row["found_rate"], (int, float))
    assert row["miss_rate"] is None or isinstance(row["miss_rate"], (int, float))


def test_stats_trends_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/stats/trends")
    assert response.status_code == 401


def test_stats_trends_returns_schema() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    response = client.get(
        "/api/stats/trends?source=all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"source", "metrics_version", "trends"}
    assert payload["source"] == "all"
    assert isinstance(payload["metrics_version"], int)
    assert isinstance(payload["trends"], list)

    if not payload["trends"]:
        return

    row = payload["trends"][0]
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
    assert row["metric_type"] == "trend"
    assert row["motif"] in allowed_motif_list()
    assert row["window_days"] in (7, 30)
    assert isinstance(row["total"], int)
    assert isinstance(row["found"], int)
    assert isinstance(row["missed"], int)
    assert isinstance(row["failed_attempt"], int)
    assert isinstance(row["unclear"], int)
    assert row["found_rate"] is None or isinstance(row["found_rate"], (int, float))
    assert row["miss_rate"] is None or isinstance(row["miss_rate"], (int, float))
