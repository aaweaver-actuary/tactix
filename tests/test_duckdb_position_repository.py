from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tactix.db.duckdb_position_repository import (
    DuckDbPositionRepository,
    default_position_dependencies,
)
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import (
    fetch_position_counts,
    fetch_positions_for_games,
    insert_positions,
)


class DuckDbPositionRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        self.repo_conn = get_connection(tmp_dir / "repo.duckdb")
        self.fn_conn = get_connection(tmp_dir / "functions.duckdb")
        init_schema(self.repo_conn)
        init_schema(self.fn_conn)
        self.repo = DuckDbPositionRepository(
            self.repo_conn,
            dependencies=default_position_dependencies(),
        )

    def tearDown(self) -> None:
        self.repo_conn.close()
        self.fn_conn.close()

    def test_repository_matches_provider_helpers(self) -> None:
        positions = self._build_positions()
        ids_repo = self.repo.insert_positions(positions)
        ids_functions = insert_positions(self.fn_conn, positions)
        self.assertEqual(ids_repo, ids_functions)

        game_ids = [pos["game_id"] for pos in positions]
        counts_repo = self.repo.fetch_position_counts(game_ids, source="lichess")
        counts_functions = fetch_position_counts(
            self.fn_conn,
            game_ids,
            source="lichess",
        )
        self.assertEqual(counts_repo, counts_functions)

        fetched_repo = self._strip_created_at(self.repo.fetch_positions_for_games(game_ids))
        fetched_functions = self._strip_created_at(
            fetch_positions_for_games(self.fn_conn, game_ids)
        )
        self.assertEqual(fetched_repo, fetched_functions)

    def _build_positions(self) -> list[dict[str, object]]:
        return [
            {
                "game_id": "game-1",
                "user": "tester",
                "source": "lichess",
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                "ply": 1,
                "move_number": 1,
                "side_to_move": "black",
                "uci": "e2e4",
                "san": "e4",
                "clock_seconds": 300,
                "is_legal": True,
            },
            {
                "game_id": "game-2",
                "user": "tester",
                "source": "lichess",
                "fen": "rnbqkbnr/pppppppp/8/8/4N3/8/PPPPPPPP/RNBQKB1R b KQkq - 1 1",
                "ply": 2,
                "move_number": 1,
                "side_to_move": "black",
                "uci": "g1f3",
                "san": "Nf3",
                "clock_seconds": 295,
                "is_legal": True,
            },
        ]

    def _strip_created_at(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        return [{key: value for key, value in row.items() if key != "created_at"} for row in rows]


if __name__ == "__main__":
    unittest.main()
