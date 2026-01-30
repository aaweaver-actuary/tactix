from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from tactix.api import app
from tactix.config import get_settings


def test_practice_queue_returns_items() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    sample = [{"tactic_id": 1, "position_id": 2, "source": "lichess"}]

    with (
        patch("tactix.get_practice_queue__api.get_connection", return_value=MagicMock()),
        patch("tactix.get_practice_queue__api.init_schema"),
        patch("tactix.get_practice_queue__api.fetch_practice_queue", return_value=sample),
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
        patch("tactix.get_practice_next__api.get_connection", return_value=MagicMock()),
        patch("tactix.get_practice_next__api.init_schema"),
        patch("tactix.get_practice_next__api.fetch_practice_queue", return_value=sample),
    ):
        response = client.get(
            "/api/practice/next?source=lichess&include_failed_attempt=0",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["item"]["tactic_id"] == 9


def test_practice_attempt_includes_latency_and_errors() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    payload = {
        "tactic_id": 1,
        "position_id": 2,
        "attempted_uci": "e2e4",
        "served_at_ms": 5000,
    }

    with (
        patch("tactix.post_practice_attempt__api.get_connection", return_value=MagicMock()),
        patch("tactix.post_practice_attempt__api.init_schema"),
        patch("tactix.post_practice_attempt__api.time_module.time", return_value=10.0),
        patch("tactix.post_practice_attempt__api.grade_practice_attempt", return_value={"status": "ok"}) as grade,
    ):
        response = client.post(
            "/api/practice/attempt",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )

    assert response.status_code == 200
    _, kwargs = grade.call_args
    assert kwargs["latency_ms"] == 5000

    with (
        patch("tactix.post_practice_attempt__api.get_connection", return_value=MagicMock()),
        patch("tactix.post_practice_attempt__api.init_schema"),
        patch("tactix.post_practice_attempt__api.grade_practice_attempt", side_effect=ValueError("bad")),
    ):
        error_response = client.post(
            "/api/practice/attempt",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )

    assert error_response.status_code == 400


def test_game_detail_missing_pgn_raises_404() -> None:
    client = TestClient(app)
    token = get_settings().api_token

    with (
        patch("tactix.get_game_detail__api.get_connection", return_value=MagicMock()),
        patch("tactix.get_game_detail__api.init_schema"),
        patch("tactix.get_game_detail__api.fetch_game_detail", return_value={"pgn": ""}),
    ):
        response = client.get(
            "/api/games/game-123?source=lichess",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404


def test_game_detail_returns_payload() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    payload = {"pgn": "1. e4 *", "game_id": "game-123"}

    with (
        patch("tactix.get_game_detail__api.get_connection", return_value=MagicMock()),
        patch("tactix.get_game_detail__api.init_schema"),
        patch("tactix.get_game_detail__api.fetch_game_detail", return_value=payload),
    ):
        response = client.get(
            "/api/games/game-123?source=lichess",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["game_id"] == "game-123"
