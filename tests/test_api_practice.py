from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from tactix.api import app
from tactix.config import get_settings


def test_practice_queue_returns_items() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    sample = [{"tactic_id": 1, "position_id": 2, "source": "lichess"}]

    with (
        patch("tactix.api.get_connection", return_value=MagicMock()),
        patch("tactix.api.init_schema"),
        patch("tactix.api.fetch_practice_queue", return_value=sample),
    ):
        response = client.get(
            "/api/practice/queue?source=lichess&include_failed_attempt=1&limit=5",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["include_failed_attempt"] is True
    assert payload["items"][0]["tactic_id"] == 1


def test_practice_next_returns_single_item() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    sample = [{"tactic_id": 9, "position_id": 10, "source": "lichess"}]

    with (
        patch("tactix.api.get_connection", return_value=MagicMock()),
        patch("tactix.api.init_schema"),
        patch("tactix.api.fetch_practice_queue", return_value=sample),
    ):
        response = client.get(
            "/api/practice/next?source=lichess&include_failed_attempt=0",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["item"]["tactic_id"] == 9
