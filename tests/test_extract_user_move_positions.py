from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import (
    fetch_positions_for_games,
    insert_positions,
)
from tactix.extract_positions import extract_positions


class ExtractUserMovePositionsTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "user_move_positions_fixture.pgn"
        )
        self.pgn = fixture_path.read_text()
        tmp_dir = Path(tempfile.mkdtemp())
        self.conn = get_connection(tmp_dir / "positions.duckdb")
        init_schema(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_positions_created_for_each_user_ply(self) -> None:
        game_id = "fixture-game-1"
        positions = extract_positions(
            self.pgn,
            user="tester",
            source="lichess",
            game_id=game_id,
        )
        self.assertEqual(len(positions), 3)
        self.assertEqual([pos["ply"] for pos in positions], [0, 2, 4])

        for position in positions:
            self.assertTrue(position["fen"])
            self.assertIsInstance(position["ply"], int)
            self.assertTrue(position["user_to_move"])
            self.assertEqual(position["game_id"], game_id)

        position_ids = insert_positions(self.conn, positions)
        self.assertEqual(len(position_ids), len(positions))

        stored_positions = fetch_positions_for_games(self.conn, [game_id])
        self.assertEqual(len(stored_positions), len(positions))

        stored_plies = sorted(row.get("ply") for row in stored_positions)
        self.assertEqual(stored_plies, [0, 2, 4])
        for earlier, later in zip(stored_plies, stored_plies[1:]):
            self.assertEqual(later - earlier, 2)

        fen_side_keys = {(row.get("fen"), row.get("side_to_move")) for row in stored_positions}
        self.assertEqual(len(fen_side_keys), len(stored_positions))
        self.assertEqual(
            len({row.get("position_id") for row in stored_positions}),
            len(stored_positions),
        )

        for row in stored_positions:
            self.assertEqual(row.get("game_id"), game_id)
            self.assertTrue(row.get("user_to_move"))
            self.assertIsNotNone(row.get("created_at"))


if __name__ == "__main__":
    unittest.main()
