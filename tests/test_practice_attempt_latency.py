import importlib
import os
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)


def test_practice_attempt_records_success_and_latency() -> None:
    tmp_dir = Path(tempfile.mkdtemp())
    db_path = tmp_dir / "practice_attempt_latency.duckdb"

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
                "game_id": "game-30",
                "user": "lichess",
                "source": "lichess",
                "fen": "8/8/8/8/8/8/8/8 w - - 0 1",
                "ply": 1,
                "move_number": 1,
                "side_to_move": "w",
                "uci": "a2a3",
                "san": "a3",
                "clock_seconds": 300,
            }
        ]
        position_ids = insert_positions(conn, positions)
        tactic_id = upsert_tactic_with_outcome(
            conn,
            {
                "game_id": "game-30",
                "position_id": position_ids[0],
                "motif": "fork",
                "severity": 1.2,
                "best_uci": "a2a4",
                "eval_cp": 120,
            },
            {"result": "missed", "user_uci": "a2a3", "eval_delta": -150},
        )

        client = TestClient(api_module.app)
        served_at_ms = int(time.time() * 1000) - 500
        response = client.post(
            "/api/practice/attempt",
            headers={"X-API-Key": "test-token"},
            json={
                "tactic_id": tactic_id,
                "position_id": position_ids[0],
                "attempted_uci": "a2a4",
                "served_at_ms": served_at_ms,
                "source": "lichess",
            },
        )
        assert response.status_code == 200

        row = conn.execute(
            "SELECT correct, success, latency_ms FROM training_attempts"
        ).fetchone()
        assert row is not None
        assert row[0] is True
        assert row[1] is True
        assert row[2] is not None
        assert int(row[2]) >= 0
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
