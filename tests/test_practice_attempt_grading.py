import tempfile
import unittest
from pathlib import Path

from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tactix.db.tactic_repository_provider import tactic_repository


class PracticeAttemptGradingTests(unittest.TestCase):
    def test_grade_practice_attempt_records_attempts(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        db_path = tmp_dir / "practice_attempts.duckdb"
        conn = get_connection(db_path)
        init_schema(conn)

        positions = [
            {
                "game_id": "game-10",
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
                "game_id": "game-10",
                "position_id": position_ids[0],
                "motif": "hanging_piece",
                "severity": 1.3,
                "best_uci": "a2a4",
                "eval_cp": 180,
            },
            {"result": "missed", "user_uci": "a2a3", "eval_delta": -240},
        )

        repo = tactic_repository(conn)
        queue = repo.fetch_practice_queue(source="lichess")
        self.assertEqual(len(queue), 1)

        result = repo.grade_practice_attempt(
            tactic_id,
            position_ids[0],
            "a2a4",
        )
        self.assertTrue(result["correct"])
        self.assertIn("a2a4", result["explanation"])
        queue_after = repo.fetch_practice_queue(source="lichess")
        self.assertEqual(len(queue_after), 0)
        rows = conn.execute(
            """
            SELECT attempted_uci, correct, best_uci, motif, severity, eval_delta
            FROM training_attempts
            ORDER BY attempt_id
            """
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "a2a4")
        self.assertTrue(rows[0][1])
        self.assertEqual(rows[0][2], "a2a4")
        self.assertEqual(rows[0][3], "hanging_piece")
        self.assertAlmostEqual(rows[0][4], 1.3)
        self.assertEqual(rows[0][5], -240)

        result = repo.grade_practice_attempt(
            tactic_id,
            position_ids[0],
            "a2a3",
        )
        self.assertFalse(result["correct"])
        count = conn.execute("SELECT COUNT(*) FROM training_attempts").fetchone()[0]
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
