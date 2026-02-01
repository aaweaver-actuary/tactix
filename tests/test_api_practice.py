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


def test_practice_next_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/practice/next")
    assert response.status_code == 401


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


def test_practice_next_returns_schema() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    sample = [
        {
            "tactic_id": 1,
            "game_id": "game-1",
            "position_id": 2,
            "source": "lichess",
            "motif": "fork",
            "result": "missed",
            "best_uci": "e2e4",
            "user_uci": "e2e3",
            "eval_delta": -120,
            "severity": 1.2,
            "created_at": "2026-02-01T00:00:00",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "position_uci": "e2e4",
            "san": "e4",
            "ply": 1,
            "move_number": 1,
            "side_to_move": "white",
            "clock_seconds": 300,
        }
    ]

    with (
        patch("tactix.get_practice_next__api.get_connection", return_value=MagicMock()),
        patch("tactix.get_practice_next__api.init_schema"),
        patch("tactix.get_practice_next__api.fetch_practice_queue", return_value=sample),
    ):
        response = client.get(
            "/api/practice/next?source=lichess&include_failed_attempt=1",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"source", "include_failed_attempt", "item"}
    assert payload["source"] == "lichess"
    assert payload["include_failed_attempt"] is True
    assert payload["item"] is not None

    required_keys = {
        "tactic_id",
        "game_id",
        "position_id",
        "source",
        "motif",
        "result",
        "best_uci",
        "user_uci",
        "eval_delta",
        "severity",
        "created_at",
        "fen",
        "position_uci",
        "san",
        "ply",
        "move_number",
        "side_to_move",
        "clock_seconds",
    }
    item = payload["item"]
    assert required_keys.issubset(item.keys())
    assert isinstance(item["tactic_id"], int)
    assert isinstance(item["position_id"], int)
    assert isinstance(item["source"], str)
    assert isinstance(item["motif"], str)
    assert isinstance(item["result"], str)
    assert isinstance(item["ply"], int)
    assert isinstance(item["move_number"], int)


def test_practice_attempt_requires_auth() -> None:
    client = TestClient(app)
    response = client.post("/api/practice/attempt", json={"tactic_id": 1})
    assert response.status_code == 401


def test_practice_attempt_returns_schema() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    payload = {
        "tactic_id": 1,
        "position_id": 2,
        "attempted_uci": "e2e4",
        "served_at_ms": 1000,
    }
    sample = {
        "attempt_id": 10,
        "tactic_id": 1,
        "position_id": 2,
        "source": "lichess",
        "attempted_uci": "e2e4",
        "best_uci": "e2e4",
        "best_san": "e4",
        "correct": True,
        "success": True,
        "motif": "fork",
        "severity": 1.4,
        "eval_delta": -120,
        "message": "Correct! fork found.",
        "explanation": "Fork on f7",
        "latency_ms": 250,
    }

    with (
        patch("tactix.post_practice_attempt__api.get_connection", return_value=MagicMock()),
        patch("tactix.post_practice_attempt__api.init_schema"),
        patch("tactix.post_practice_attempt__api.grade_practice_attempt", return_value=sample),
    ):
        response = client.post(
            "/api/practice/attempt",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )

    assert response.status_code == 200
    body = response.json()
    required_keys = {
        "attempt_id",
        "tactic_id",
        "position_id",
        "source",
        "attempted_uci",
        "best_uci",
        "best_san",
        "correct",
        "success",
        "motif",
        "severity",
        "eval_delta",
        "message",
        "explanation",
        "latency_ms",
    }
    assert required_keys.issubset(body.keys())
    assert isinstance(body["attempt_id"], int)
    assert isinstance(body["tactic_id"], int)
    assert isinstance(body["position_id"], int)
    assert isinstance(body["attempted_uci"], str)
    assert isinstance(body["best_uci"], str)
    assert isinstance(body["correct"], bool)
    assert isinstance(body["success"], bool)
    assert isinstance(body["motif"], str)
    assert isinstance(body["severity"], float)
    assert isinstance(body["eval_delta"], int)
    assert isinstance(body["message"], str)


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
        patch(
            "tactix.post_practice_attempt__api.grade_practice_attempt",
            return_value={"status": "ok"},
        ) as grade,
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
        patch(
            "tactix.post_practice_attempt__api.grade_practice_attempt",
            side_effect=ValueError("bad"),
        ),
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
