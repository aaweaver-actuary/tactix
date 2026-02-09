import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tactix.db.dashboard_repository_provider import fetch_metrics, fetch_motif_stats
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tactix.db.metrics_repository_provider import update_metrics_summary
from tactix.db.raw_pgn_repository_provider import upsert_raw_pgns
from tactix.pgn_utils import (
    extract_game_id,
    extract_last_timestamp_ms,
    split_pgn_chunks,
)


class MetricsRefreshTests(unittest.TestCase):
    def test_metrics_refresh_includes_trends_and_breakdowns(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        db_path = tmp_dir / "metrics.duckdb"
        conn = get_connection(db_path)
        init_schema(conn)

        fixture_path = Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
        chunks = split_pgn_chunks(fixture_path.read_text())
        rows = []
        for chunk in chunks:
            rows.append(
                {
                    "game_id": extract_game_id(chunk),
                    "user": "lichess",
                    "source": "lichess",
                    "fetched_at": datetime.now(timezone.utc),
                    "pgn": chunk,
                    "last_timestamp_ms": extract_last_timestamp_ms(chunk),
                }
            )
        upsert_raw_pgns(conn, rows)

        positions = []
        for idx, row in enumerate(rows, start=1):
            positions.append(
                {
                    "game_id": row["game_id"],
                    "user": "lichess",
                    "source": "lichess",
                    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                    "ply": idx,
                    "move_number": idx,
                    "side_to_move": "w",
                    "uci": "e2e4",
                    "san": "e4",
                    "clock_seconds": 600,
                }
            )
        position_ids = insert_positions(conn, positions)

        for pos, position_id in zip(positions, position_ids, strict=False):
            upsert_tactic_with_outcome(
                conn,
                {
                    "game_id": pos["game_id"],
                    "position_id": position_id,
                    "motif": "hanging_piece",
                    "severity": 1.2,
                    "best_uci": "e2e4",
                    "eval_cp": 120,
                },
                {"result": "found", "user_uci": "e2e4", "eval_delta": 30},
            )

        update_metrics_summary(conn)
        metrics = fetch_metrics(conn, source="lichess")

        breakdowns = [m for m in metrics if m.get("metric_type") == "motif_breakdown"]
        trends = [m for m in metrics if m.get("metric_type") == "trend"]
        self.assertTrue(breakdowns)
        self.assertTrue(trends)
        self.assertTrue(any(m.get("window_days") == 7 for m in trends))
        self.assertTrue(any(m.get("window_days") == 30 for m in trends))
        for row in trends:
            self.assertIsNotNone(row.get("trend_date"))
            self.assertIsNotNone(row.get("found_rate"))

    def test_metrics_refresh_rolls_over_games(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        db_path = tmp_dir / "metrics_games.duckdb"
        conn = get_connection(db_path)
        init_schema(conn)

        base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        results = [
            "found",
            "missed",
            "found",
            "missed",
            "found",
            "missed",
            "found",
            "missed",
        ]
        rows = []
        for idx, result in enumerate(results, start=1):
            game_id = f"game-{idx}"
            timestamp = int((base_time + timedelta(minutes=idx)).timestamp() * 1000)
            rows.append(
                {
                    "game_id": game_id,
                    "user": "lichess",
                    "source": "lichess",
                    "fetched_at": base_time,
                    "pgn": (
                        '[Event "Test"]\n'
                        f'[Site "https://lichess.org/{game_id}"]\n'
                        '[White "lichess"]\n'
                        '[Black "opponent"]\n'
                        '[Result "1-0"]\n\n'
                        "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0"
                    ),
                    "last_timestamp_ms": timestamp,
                }
            )
        upsert_raw_pgns(conn, rows)

        positions = []
        for idx, row in enumerate(rows, start=1):
            positions.append(
                {
                    "game_id": row["game_id"],
                    "user": "lichess",
                    "source": "lichess",
                    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                    "ply": idx,
                    "move_number": idx,
                    "side_to_move": "w",
                    "uci": "e2e4",
                    "san": "e4",
                    "clock_seconds": 600,
                }
            )
        position_ids = insert_positions(conn, positions)

        for pos, position_id, result in zip(positions, position_ids, results, strict=False):
            upsert_tactic_with_outcome(
                conn,
                {
                    "game_id": pos["game_id"],
                    "position_id": position_id,
                    "motif": "hanging_piece",
                    "severity": 1.0,
                    "best_uci": "e2e4",
                    "eval_cp": 120,
                },
                {"result": result, "user_uci": "e2e4", "eval_delta": 30},
            )

        update_metrics_summary(conn)
        metrics = fetch_metrics(conn, source="lichess")

        trends_7 = [
            row
            for row in metrics
            if row.get("metric_type") == "trend"
            and row.get("motif") == "hanging_piece"
            and row.get("window_days") == 7
        ]
        trends_30 = [
            row
            for row in metrics
            if row.get("metric_type") == "trend"
            and row.get("motif") == "hanging_piece"
            and row.get("window_days") == 30
        ]
        self.assertEqual(len(trends_7), len(results))
        self.assertEqual(len(trends_30), len(results))
        self.assertTrue(all(row.get("total") == 1 for row in trends_7))

        expected_7 = []
        expected_30 = []
        numeric_results = [1 if r == "found" else 0 for r in results]
        for idx in range(len(numeric_results)):
            window_7 = numeric_results[max(0, idx - 6) : idx + 1]
            window_30 = numeric_results[max(0, idx - 29) : idx + 1]
            expected_7.append(round(sum(window_7) / len(window_7), 4))
            expected_30.append(round(sum(window_30) / len(window_30), 4))

        found_rates_7 = sorted(round(float(row["found_rate"]), 4) for row in trends_7)
        found_rates_30 = sorted(round(float(row["found_rate"]), 4) for row in trends_30)
        self.assertEqual(found_rates_7, sorted(expected_7))
        self.assertEqual(found_rates_30, sorted(expected_30))

    def test_metrics_refresh_time_trouble_correlation_by_time_control(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        db_path = tmp_dir / "metrics_time_trouble.duckdb"
        conn = get_connection(db_path)
        init_schema(conn)

        base_time = datetime(2024, 1, 2, tzinfo=timezone.utc)
        scenarios = [
            ("300+0", 20, "missed"),
            ("300+0", 25, "missed"),
            ("300+0", 100, "found"),
            ("300+0", 120, "found"),
            ("600+5", 20, "found"),
            ("600+5", 25, "found"),
            ("600+5", 100, "missed"),
            ("600+5", 120, "missed"),
        ]

        rows = []
        positions = []
        for idx, (time_control, clock_seconds, result) in enumerate(scenarios, start=1):
            game_id = f"game-{idx}"
            timestamp = int((base_time + timedelta(minutes=idx)).timestamp() * 1000)
            rows.append(
                {
                    "game_id": game_id,
                    "user": "lichess",
                    "source": "lichess",
                    "fetched_at": base_time,
                    "pgn": (
                        '[Event "Test"]\n'
                        f'[Site "https://lichess.org/{game_id}"]\n'
                        '[White "lichess"]\n'
                        '[Black "opponent"]\n'
                        '[Result "1-0"]\n'
                        f'[TimeControl "{time_control}"]\n\n'
                        "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0"
                    ),
                    "last_timestamp_ms": timestamp,
                }
            )
            positions.append(
                {
                    "game_id": game_id,
                    "user": "lichess",
                    "source": "lichess",
                    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                    "ply": idx,
                    "move_number": idx,
                    "side_to_move": "w",
                    "uci": "e2e4",
                    "san": "e4",
                    "clock_seconds": clock_seconds,
                    "result": result,
                }
            )

        upsert_raw_pgns(conn, rows)
        position_ids = insert_positions(conn, positions)

        for pos, position_id in zip(positions, position_ids, strict=False):
            upsert_tactic_with_outcome(
                conn,
                {
                    "game_id": pos["game_id"],
                    "position_id": position_id,
                    "motif": "hanging_piece",
                    "severity": 1.0,
                    "best_uci": "e2e4",
                    "eval_cp": 120,
                },
                {
                    "result": pos["result"],
                    "user_uci": "e2e4",
                    "eval_delta": 30,
                },
            )

        update_metrics_summary(conn)
        metrics = fetch_metrics(conn, source="lichess")
        time_trouble = [
            row for row in metrics if row.get("metric_type") == "time_trouble_correlation"
        ]

        self.assertEqual(len(time_trouble), 2)
        by_control = {row.get("time_control"): row for row in time_trouble}
        self.assertIn("300+0", by_control)
        self.assertIn("600+5", by_control)

        self.assertEqual(by_control["300+0"].get("total"), 4)
        self.assertEqual(by_control["600+5"].get("total"), 4)
        self.assertAlmostEqual(float(by_control["300+0"]["miss_rate"]), 0.5, places=4)
        self.assertAlmostEqual(float(by_control["600+5"]["miss_rate"]), 0.5, places=4)
        self.assertAlmostEqual(float(by_control["300+0"]["found_rate"]), 1.0, places=4)
        self.assertAlmostEqual(float(by_control["600+5"]["found_rate"]), -1.0, places=4)

    def test_fetch_motif_stats_coerces_rates(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        db_path = tmp_dir / "metrics_stats.duckdb"
        conn = get_connection(db_path)
        init_schema(conn)

        fixture_path = Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
        chunks = split_pgn_chunks(fixture_path.read_text())
        rows = []
        for chunk in chunks:
            rows.append(
                {
                    "game_id": extract_game_id(chunk),
                    "user": "lichess",
                    "source": "lichess",
                    "fetched_at": datetime.now(timezone.utc),
                    "pgn": chunk,
                    "last_timestamp_ms": extract_last_timestamp_ms(chunk),
                }
            )
        upsert_raw_pgns(conn, rows)

        positions = []
        for idx, row in enumerate(rows, start=1):
            positions.append(
                {
                    "game_id": row["game_id"],
                    "user": "lichess",
                    "source": "lichess",
                    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                    "ply": idx,
                    "move_number": idx,
                    "side_to_move": "w",
                    "uci": "e2e4",
                    "san": "e4",
                    "clock_seconds": 600,
                }
            )
        position_ids = insert_positions(conn, positions)

        for pos, position_id in zip(positions, position_ids, strict=False):
            upsert_tactic_with_outcome(
                conn,
                {
                    "game_id": pos["game_id"],
                    "position_id": position_id,
                    "motif": "hanging_piece",
                    "severity": 1.2,
                    "best_uci": "e2e4",
                    "eval_cp": 120,
                },
                {"result": "found", "user_uci": "e2e4", "eval_delta": 30},
            )

        update_metrics_summary(conn)
        stats = fetch_motif_stats(conn, source="lichess")
        self.assertTrue(stats)
        row = stats[0]
        self.assertEqual(row.get("metric_type"), "motif_breakdown")
        self.assertIsInstance(row.get("total"), int)
        self.assertIsInstance(row.get("found_rate"), float)
        self.assertIsInstance(row.get("miss_rate"), float)


if __name__ == "__main__":
    unittest.main()
