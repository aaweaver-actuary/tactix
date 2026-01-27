from fastapi.testclient import TestClient

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
    response = client.get(
        "/api/postgres/status", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["status"] == "disabled"
    assert payload["events"] == []
