from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tactix.dashboard_query import DashboardQuery
from tactix.db.dashboard_repository_provider import fetch_metrics
from tactix.db.duckdb_metrics_repository import (
    DuckDbMetricsRepository,
    default_metrics_dependencies,
)
from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)
from tactix.db.metrics_repository_provider import update_metrics_summary
from tactix.db.raw_pgn_repository_provider import upsert_raw_pgns

PGN_TEMPLATE = """[Event "Test"]
[Site "https://example.org/{site}"]
[UTCDate "2024.01.01"]
[UTCTime "00:00:01"]
[White "tester"]
[Black "opponent"]
[WhiteElo "{white_elo}"]
[BlackElo "{black_elo}"]
[TimeControl "{time_control}"]
[Result "*"]

1. e4 *
"""


class DuckDbMetricsRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.conn = get_connection(self.tmp_dir / "metrics.duckdb")
        init_schema(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_repository_matches_store_update(self) -> None:
        self._insert_dashboard_rows()

        update_metrics_summary(self.conn)
        legacy_rows = self._sorted_rows(fetch_metrics(self.conn, DashboardQuery(source="all")))

        repo = DuckDbMetricsRepository(self.conn, dependencies=default_metrics_dependencies())
        repo.update_metrics_summary()
        repo_rows = self._sorted_rows(fetch_metrics(self.conn, DashboardQuery(source="all")))

        self.assertEqual(legacy_rows, repo_rows)

    def _insert_dashboard_rows(self) -> None:
        scenarios = [
            {
                "source": "lichess",
                "game_id": "g-lichess",
                "time_control": "300+0",
                "rating": 1400,
                "motif": "fork",
                "result": "found",
                "clock_seconds": 25,
                "last_timestamp_ms": 5,
            },
            {
                "source": "chesscom",
                "game_id": "g-chesscom",
                "time_control": "600+5",
                "rating": 1500,
                "motif": "pin",
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
