from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tactix.dashboard_query import DashboardQuery
from tactix.db.duckdb_dashboard_repository import (
    DuckDbDashboardRepository,
    default_dashboard_repository_dependencies,
)
from tactix.db.dashboard_repository_provider import (
    fetch_metrics,
    fetch_opportunity_motif_counts,
    fetch_pipeline_table_counts,
    fetch_recent_games,
    fetch_recent_positions,
    fetch_recent_tactics,
)
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tactix.db.metrics_repository_provider import update_metrics_summary
from tactix.db.raw_pgn_repository_provider import upsert_raw_pgns

PGN_TEMPLATE = """[Event \"Test\"]
[Site \"https://example.org/{site}\"]
[UTCDate \"2024.01.01\"]
[UTCTime \"00:00:01\"]
[White \"tester\"]
[Black \"opponent\"]
[WhiteElo \"{white_elo}\"]
[BlackElo \"{black_elo}\"]
[TimeControl \"{time_control}\"]
[Result \"*\"]

1. e4 *
"""


class DuckDbDashboardRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.conn = get_connection(self.tmp_dir / "dash.duckdb")
        init_schema(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_repository_matches_store_functions(self) -> None:
        self._insert_dashboard_rows()
        update_metrics_summary(self.conn)

        repo = self._build_repository()
        all_query = DashboardQuery(source="all")
        lichess_query = DashboardQuery(source="lichess")

        self.assertEqual(
            self._sorted_rows(repo.fetch_metrics(all_query)),
            self._sorted_rows(fetch_metrics(self.conn, all_query)),
        )
        self.assertEqual(
            repo.fetch_recent_games(all_query),
            fetch_recent_games(self.conn, all_query, user="tester"),
        )
        self.assertEqual(
            repo.fetch_recent_positions(lichess_query),
            fetch_recent_positions(self.conn, lichess_query),
        )
        self.assertEqual(
            repo.fetch_recent_tactics(lichess_query),
            fetch_recent_tactics(self.conn, lichess_query),
        )
        self.assertEqual(
            repo.fetch_pipeline_table_counts(lichess_query),
            fetch_pipeline_table_counts(self.conn, lichess_query),
        )
        self.assertEqual(
            repo.fetch_opportunity_motif_counts(lichess_query),
            fetch_opportunity_motif_counts(self.conn, lichess_query),
        )

    def _build_repository(self) -> DuckDbDashboardRepository:
        return DuckDbDashboardRepository(
            self.conn,
            dependencies=default_dashboard_repository_dependencies(),
        )

    def _insert_dashboard_rows(self) -> None:
        scenarios = [
            {
                "source": "lichess",
                "game_id": "g-lichess",
                "time_control": "300+0",
                "rating": 1400,
                "motif": "hanging_piece",
                "result": "found",
                "clock_seconds": 25,
                "last_timestamp_ms": 5,
            },
            {
                "source": "chesscom",
                "game_id": "g-chesscom",
                "time_control": "600+5",
                "rating": 1500,
                "motif": "hanging_piece",
                "result": "missed",
                "clock_seconds": 15,
                "last_timestamp_ms": 10,
            },
        ]
        for scenario in scenarios:
            pgn = PGN_TEMPLATE.format(
                site=scenario["game_id"],
                white_elo=scenario["rating"],
                black_elo=scenario["rating"] + 50,
                time_control=scenario["time_control"],
            )
            upsert_raw_pgns(
                self.conn,
                [
                    {
                        "game_id": scenario["game_id"],
                        "user": "tester",
                        "source": scenario["source"],
                        "pgn": pgn,
                        "last_timestamp_ms": scenario["last_timestamp_ms"],
                    }
                ],
            )
            position_ids = insert_positions(
                self.conn,
                [
                    {
                        "game_id": scenario["game_id"],
                        "user": "tester",
                        "source": scenario["source"],
                        "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                        "ply": 1,
                        "move_number": 1,
                        "side_to_move": "black",
                        "uci": "e2e4",
                        "san": "e4",
                        "clock_seconds": scenario["clock_seconds"],
                        "is_legal": True,
                    }
                ],
            )
            upsert_tactic_with_outcome(
                self.conn,
                {
                    "game_id": scenario["game_id"],
                    "position_id": position_ids[0],
                    "motif": scenario["motif"],
                    "severity": 1.0,
                    "best_uci": "e2e4",
                    "best_san": "e4",
                    "explanation": "test",
                    "eval_cp": 50,
                },
                {
                    "result": scenario["result"],
                    "user_uci": "e2e4",
                    "eval_delta": 0,
                },
            )

    def _sorted_rows(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        return sorted(
            rows,
            key=lambda row: (
                row.get("source"),
                row.get("metric_type"),
                row.get("motif"),
                row.get("window_days"),
                row.get("trend_date"),
                row.get("game_id"),
            ),
        )


if __name__ == "__main__":
    unittest.main()
