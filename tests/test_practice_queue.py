import tempfile
import unittest
from pathlib import Path

from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)
from tactix.db.tactic_repository_provider import tactic_repository


class PracticeQueueTests(unittest.TestCase):
    def test_practice_queue_filters_missed_only(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        db_path = tmp_dir / "practice.duckdb"
        conn = get_connection(db_path)
        init_schema(conn)
        repo = tactic_repository(conn)

        positions = [
            {
                "game_id": "game-1",
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
                "game_id": "game-2",
                "user": "lichess",
                "source": "lichess",
                "fen": "8/8/8/8/8/8/8/8 w - - 0 1",
                "ply": 2,
                "move_number": 2,
                "side_to_move": "w",
                "uci": "b2b3",
                "san": "b3",
                "clock_seconds": 280,
            },
            {
                "game_id": "game-3",
                "user": "chesscom",
                "source": "chesscom",
                "fen": "8/8/8/8/8/8/8/8 w - - 0 1",
                "ply": 3,
                "move_number": 3,
                "side_to_move": "w",
                "uci": "c2c3",
                "san": "c3",
                "clock_seconds": 250,
            },
        ]

        position_ids = insert_positions(conn, positions)

        upsert_tactic_with_outcome(
            conn,
            {
                "game_id": "game-1",
                "position_id": position_ids[0],
                "motif": "fork",
                "severity": 1.5,
                "best_uci": "a2a4",
                "eval_cp": 200,
            },
            {"result": "missed", "user_uci": "a2a3", "eval_delta": -350},
        )
        upsert_tactic_with_outcome(
            conn,
            {
                "game_id": "game-2",
                "position_id": position_ids[1],
                "motif": "pin",
                "severity": 0.8,
                "best_uci": "b2b4",
                "eval_cp": 120,
            },
            {"result": "found", "user_uci": "b2b3", "eval_delta": 10},
        )
        upsert_tactic_with_outcome(
            conn,
            {
                "game_id": "game-3",
                "position_id": position_ids[2],
                "motif": "skewer",
                "severity": 1.1,
                "best_uci": "c2c4",
                "eval_cp": 180,
            },
            {"result": "missed", "user_uci": "c2c3", "eval_delta": -320},
        )

        queue = repo.fetch_practice_queue(source="lichess")
        self.assertTrue(queue)
        self.assertTrue(all(item["result"] == "missed" for item in queue))
        self.assertTrue(all(item["source"] == "lichess" for item in queue))

    def test_practice_queue_includes_failed_attempt_when_enabled(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        db_path = tmp_dir / "practice_failed.duckdb"
        conn = get_connection(db_path)
        init_schema(conn)
        repo = tactic_repository(conn)

        positions = [
            {
                "game_id": "game-4",
                "user": "lichess",
                "source": "lichess",
                "fen": "8/8/8/8/8/8/8/8 w - - 0 1",
                "ply": 4,
                "move_number": 4,
                "side_to_move": "w",
                "uci": "d2d3",
                "san": "d3",
                "clock_seconds": 240,
            },
            {
                "game_id": "game-5",
                "user": "lichess",
                "source": "lichess",
                "fen": "8/8/8/8/8/8/8/8 w - - 0 1",
                "ply": 5,
                "move_number": 5,
                "side_to_move": "w",
                "uci": "e2e3",
                "san": "e3",
                "clock_seconds": 220,
            },
        ]
        position_ids = insert_positions(conn, positions)

        upsert_tactic_with_outcome(
            conn,
            {
                "game_id": "game-4",
                "position_id": position_ids[0],
                "motif": "fork",
                "severity": 1.2,
                "best_uci": "d2d4",
                "eval_cp": 210,
            },
            {"result": "failed_attempt", "user_uci": "d2d3", "eval_delta": -120},
        )
        upsert_tactic_with_outcome(
            conn,
            {
                "game_id": "game-5",
                "position_id": position_ids[1],
                "motif": "fork",
                "severity": 1.0,
                "best_uci": "e2e4",
                "eval_cp": 190,
            },
            {"result": "unclear", "user_uci": "e2e3", "eval_delta": -20},
        )

        queue = repo.fetch_practice_queue(source="lichess", include_failed_attempt=True)
        results = {item["result"] for item in queue}
        self.assertIn("failed_attempt", results)
        self.assertNotIn("unclear", results)


if __name__ == "__main__":
    unittest.main()
