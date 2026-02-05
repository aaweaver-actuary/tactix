from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tactix.db.duckdb_tactic_repository import (
    DuckDbTacticRepository,
    default_tactic_dependencies,
)
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tactix.db.raw_pgn_repository_provider import upsert_raw_pgns

PGN_TEMPLATE = """[Event \"Test\"]
[Site \"https://lichess.org/Game123\"]
[UTCDate \"2020.01.02\"]
[UTCTime \"03:04:05\"]
[White \"tester\"]
[Black \"opponent\"]
[WhiteElo \"1500\"]
[BlackElo \"1400\"]
[TimeControl \"300+0\"]
[Result \"1-0\"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1-0
"""


class DuckDbTacticRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        self.repo_conn = get_connection(tmp_dir / "repo.duckdb")
        self.fn_conn = get_connection(tmp_dir / "functions.duckdb")
        init_schema(self.repo_conn)
        init_schema(self.fn_conn)
        self.repo = DuckDbTacticRepository(
            self.repo_conn,
            dependencies=default_tactic_dependencies(),
        )
        self.fn_repo = DuckDbTacticRepository(
            self.fn_conn,
            dependencies=default_tactic_dependencies(),
        )

    def tearDown(self) -> None:
        self.repo_conn.close()
        self.fn_conn.close()

    def test_repository_matches_provider_helpers(self) -> None:
        self._seed_raw_pgns()
        position_row = self._build_position()
        position_id_repo = insert_positions(self.repo_conn, [position_row])[0]
        position_id_fn = insert_positions(self.fn_conn, [position_row])[0]

        tactic_row = {
            "game_id": position_row["game_id"],
            "position_id": position_id_repo,
            "motif": "fork",
            "severity": 1.2,
            "best_uci": "e2e4",
            "best_san": "e4",
            "explanation": "test",
            "eval_cp": 50,
        }
        outcome_row = {
            "result": "missed",
            "user_uci": "e2e4",
            "eval_delta": -10,
        }

        tactic_id_repo = self.repo.upsert_tactic_with_outcome(tactic_row, outcome_row)
        tactic_row_fn = dict(tactic_row, position_id=position_id_fn)
        tactic_id_fn = upsert_tactic_with_outcome(
            self.fn_conn,
            tactic_row_fn,
            outcome_row,
        )
        self.assertEqual(tactic_id_repo, tactic_id_fn)

        practice_tactic_repo = self.repo.fetch_practice_tactic(tactic_id_repo)
        practice_tactic_fn = self.fn_repo.fetch_practice_tactic(tactic_id_fn)
        self.assertEqual(practice_tactic_repo, practice_tactic_fn)

        queue_repo = self._strip_created_at(
            self.repo.fetch_practice_queue(source="lichess", include_failed_attempt=True)
        )
        queue_fn = self._strip_created_at(
            self.fn_repo.fetch_practice_queue(
                source="lichess",
                include_failed_attempt=True,
            )
        )
        self.assertEqual(queue_repo, queue_fn)

        grade_repo = self.repo.grade_practice_attempt(
            tactic_id_repo,
            position_id_repo,
            attempted_uci="e2e4",
            latency_ms=120,
        )
        grade_fn = self.fn_repo.grade_practice_attempt(
            tactic_id_fn,
            position_id_fn,
            attempted_uci="e2e4",
            latency_ms=120,
        )
        self.assertEqual(grade_repo, grade_fn)

        detail_repo = self._normalize_detail(
            self.repo.fetch_game_detail(
                position_row["game_id"],
                user="tester",
                source="lichess",
            )
        )
        detail_fn = self._normalize_detail(
            self.fn_repo.fetch_game_detail(
                position_row["game_id"],
                user="tester",
                source="lichess",
            )
        )
        self.assertEqual(detail_repo, detail_fn)

    def _seed_raw_pgns(self) -> None:
        payload = {
            "game_id": "game-lichess",
            "user": "tester",
            "source": "lichess",
            "pgn": PGN_TEMPLATE,
            "last_timestamp_ms": 10,
        }
        upsert_raw_pgns(self.repo_conn, [payload])
        upsert_raw_pgns(self.fn_conn, [payload])

    def _build_position(self) -> dict[str, object]:
        return {
            "game_id": "game-lichess",
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
        }

    def _strip_created_at(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        return [{key: value for key, value in row.items() if key != "created_at"} for row in rows]

    def _normalize_detail(self, detail: dict[str, object]) -> dict[str, object]:
        normalized = dict(detail)
        analysis_rows = detail.get("analysis", [])
        normalized["analysis"] = [
            {key: value for key, value in row.items() if key != "created_at"}
            for row in analysis_rows
        ]
        return normalized


if __name__ == "__main__":
    unittest.main()
