from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from tactix.db._rows_to_dicts import _rows_to_dicts
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import (
    fetch_positions_for_games,
    insert_positions,
)
from tactix.define_base_db_store__db_store import BaseDbStore
from tactix.extract_last_timestamp_ms import extract_last_timestamp_ms
from tactix.extract_positions import extract_positions


class UserMovesViewTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "user_move_positions_fixture.pgn"
        )
        self.pgn = fixture_path.read_text()
        self.game_id = "fixture-game-1"
        self.user = "tester"
        self.source = "chesscom"
        tmp_dir = Path(tempfile.mkdtemp())
        self.conn = get_connection(tmp_dir / "user_moves.duckdb")
        init_schema(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_user_moves_view_matches_positions(self) -> None:
        last_timestamp_ms = extract_last_timestamp_ms(self.pgn)
        pgn_hash = BaseDbStore.hash_pgn(self.pgn)
        self.conn.execute(
            """
            INSERT INTO raw_pgns (
                raw_pgn_id,
                game_id,
                user,
                source,
                fetched_at,
                pgn,
                pgn_hash,
                pgn_version,
                user_rating,
                time_control,
                ingested_at,
                last_timestamp_ms,
                cursor
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                1,
                self.game_id,
                self.user,
                self.source,
                None,
                self.pgn,
                pgn_hash,
                1,
                None,
                None,
                None,
                last_timestamp_ms,
                None,
            ],
        )

        positions = extract_positions(
            self.pgn,
            user=self.user,
            source=self.source,
            game_id=self.game_id,
        )
        insert_positions(self.conn, positions)
        stored_positions = fetch_positions_for_games(self.conn, [self.game_id])
        position_by_id = {
            row.get("position_id"): row for row in stored_positions if row.get("position_id")
        }

        moves_result = self.conn.execute(
            "SELECT * FROM user_moves WHERE game_id = ? ORDER BY position_id",
            [self.game_id],
        )
        user_moves = _rows_to_dicts(moves_result)

        self.assertEqual(len(user_moves), len(position_by_id))
        self.assertEqual(len({row.get("position_id") for row in user_moves}), len(user_moves))

        expected_side = "white"
        for row in stored_positions:
            self.assertEqual(row.get("side_to_move"), expected_side)
            self.assertTrue(row.get("user_to_move"))

        expected_played_at = datetime.fromtimestamp(last_timestamp_ms / 1000, tz=UTC)
        for row in user_moves:
            position_id = row.get("position_id")
            self.assertIsNotNone(position_id)
            self.assertIn(position_id, position_by_id)
            self.assertEqual(row.get("user_move_id"), position_id)
            self.assertEqual(
                row.get("played_uci"),
                position_by_id[position_id].get("uci"),
            )
            self.assertIsNotNone(row.get("created_at"))
            played_at = row.get("played_at")
            self.assertIsNotNone(played_at)
            if isinstance(played_at, datetime):
                if played_at.tzinfo is None:
                    played_at = played_at.replace(tzinfo=UTC)
                self.assertEqual(played_at, expected_played_at)
            else:
                parsed = datetime.fromisoformat(str(played_at))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                self.assertEqual(parsed, expected_played_at)


if __name__ == "__main__":
    unittest.main()
