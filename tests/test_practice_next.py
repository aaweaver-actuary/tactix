import importlib
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    record_training_attempt,
    upsert_tactic_with_outcome,
)


def test_practice_next_excludes_seen_tactics() -> None:
    tmp_dir = Path(tempfile.mkdtemp())
    db_path = tmp_dir / "practice_next.duckdb"

    old_db = os.environ.get("TACTIX_DUCKDB_PATH")
    old_token = os.environ.get("TACTIX_API_TOKEN")
    old_source = os.environ.get("TACTIX_SOURCE")

    os.environ["TACTIX_DUCKDB_PATH"] = str(db_path)
    os.environ["TACTIX_API_TOKEN"] = "test-token"
    os.environ["TACTIX_SOURCE"] = "lichess"

    try:
        import tactix.api as api_module
        import tactix.config as config_module

        importlib.reload(config_module)
        importlib.reload(api_module)

        conn = get_connection(db_path)
        init_schema(conn)

        positions = [
            {
                "game_id": "game-20",
                "user": "lichess",
                "source": "lichess",
                "fen": "8/8/8/8/8/8/8/8 w - - 0 1",
                "ply": 1,
                "move_number": 1,
                "side_to_move": "w",
                "uci": "a2a3",
                "san": "a3",
                "clock_seconds": 300,
            },
            {
                "game_id": "game-21",
                "user": "lichess",
                "source": "lichess",
                "fen": "8/8/8/8/8/8/8/8 w - - 0 1",
                "ply": 2,
                "move_number": 2,
                "side_to_move": "w",
                "uci": "b2b3",
                "san": "b3",
                "clock_seconds": 290,
            },
        ]
        position_ids = insert_positions(conn, positions)

        seen_tactic_id = upsert_tactic_with_outcome(
            conn,
            {
                "game_id": "game-20",
                "position_id": position_ids[0],
                "motif": "fork",
                "severity": 1.4,
                "best_uci": "a2a4",
                "eval_cp": 160,
            },
            {"result": "missed", "user_uci": "a2a3", "eval_delta": -200},
        )
        unseen_tactic_id = upsert_tactic_with_outcome(
            conn,
            {
                "game_id": "game-21",
                "position_id": position_ids[1],
                "motif": "pin",
                "severity": 0.9,
                "best_uci": "b2b4",
                "eval_cp": 140,
            },
            {"result": "missed", "user_uci": "b2b3", "eval_delta": -180},
        )

        record_training_attempt(
            conn,
            {
                "tactic_id": seen_tactic_id,
                "position_id": position_ids[0],
                "source": "lichess",
                "attempted_uci": "a2a4",
                "correct": True,
                "best_uci": "a2a4",
                "motif": "fork",
                "severity": 1.4,
                "eval_delta": -200,
            },
        )

        client = TestClient(api_module.app)
        response = client.get("/api/practice/next", headers={"X-API-Key": "test-token"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["item"] is not None
        assert payload["item"]["tactic_id"] == unseen_tactic_id
        assert payload["item"]["tactic_id"] != seen_tactic_id
    finally:
        if old_db is None:
            os.environ.pop("TACTIX_DUCKDB_PATH", None)
        else:
            os.environ["TACTIX_DUCKDB_PATH"] = old_db
        if old_token is None:
            os.environ.pop("TACTIX_API_TOKEN", None)
        else:
            os.environ["TACTIX_API_TOKEN"] = old_token
        if old_source is None:
            os.environ.pop("TACTIX_SOURCE", None)
        else:
            os.environ["TACTIX_SOURCE"] = old_source
