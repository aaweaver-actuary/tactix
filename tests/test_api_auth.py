from fastapi.testclient import TestClient

from tactix.api import app
from tactix.config import get_settings


def test_health_is_unauthenticated():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200


def test_requires_auth_for_dashboard():
    client = TestClient(app)
    response = client.get("/api/dashboard")
    assert response.status_code == 401


def test_allows_authorization_header():
    client = TestClient(app)
    token = get_settings().api_token
    response = client.get(
        "/api/dashboard", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_allows_api_key_header():
    client = TestClient(app)
    token = get_settings().api_token
    response = client.get("/api/practice/queue", headers={"X-API-Key": token})
    assert response.status_code == 200
