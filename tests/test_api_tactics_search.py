from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tactix.api import app
from tactix.app.use_cases.tactics_search import get_tactics_search_use_case
from tactix.config import get_settings


def test_tactics_search_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/tactics/search")
    assert response.status_code == 401


def test_tactics_search_returns_schema() -> None:
    client = TestClient(app)
    token = get_settings().api_token
    sample = [
        {
            "tactic_id": 1,
            "game_id": "game-1",
            "position_id": 2,
            "source": "lichess",
            "motif": "fork",
            "result": "found",
            "user_uci": "e2e4",
            "eval_delta": -120,
            "severity": 1.2,
            "created_at": "2026-02-01T00:00:00",
            "best_uci": "e2e4",
            "best_san": "e4",
            "explanation": "Fork on f7",
            "eval_cp": 150,
        }
    ]

    use_case = MagicMock()
    use_case.search.return_value = {
        "source": "all",
        "limit": 5,
        "tactics": sample,
    }
    app.dependency_overrides[get_tactics_search_use_case] = lambda: use_case
    try:
        response = client.get(
            "/api/tactics/search?source=all&limit=5&motif=fork",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides = {}

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"source", "limit", "tactics"}
    assert payload["source"] == "all"
    assert payload["limit"] == 5
    assert isinstance(payload["tactics"], list)

    row = payload["tactics"][0]
    required_keys = {
        "tactic_id",
        "game_id",
        "position_id",
        "source",
        "motif",
        "result",
        "user_uci",
        "eval_delta",
        "severity",
        "created_at",
        "best_uci",
        "best_san",
        "explanation",
        "eval_cp",
    }
    assert required_keys.issubset(row.keys())
    assert isinstance(row["tactic_id"], int)
    assert isinstance(row["motif"], str)
