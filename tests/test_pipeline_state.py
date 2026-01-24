import shutil
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import chess.engine

from tactix.config import Settings
from tactix.duckdb_store import fetch_version, get_connection
from tactix.lichess_client import read_checkpoint
from tactix.chesscom_client import read_cursor
from tactix.pipeline import run_daily_game_sync


class PipelineStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
        )
        self.chesscom_fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_blitz_sample.pgn"
        )

    def test_checkpoint_and_metrics_files_written(self) -> None:
        settings = Settings(
            duckdb_path=self.tmp_dir / "tactix.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            fixture_pgn_path=self.fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        )

        result = run_daily_game_sync(settings)

        self.assertGreater(result["metrics_version"], 0)
        self.assertTrue(settings.metrics_version_file.exists())
        self.assertEqual(
            int(settings.metrics_version_file.read_text().strip()),
            result["metrics_version"],
        )

        ckpt_value = read_checkpoint(settings.checkpoint_path)
        self.assertGreater(ckpt_value, 0)
        self.assertEqual(ckpt_value, int(settings.checkpoint_path.read_text().strip()))

    def test_chesscom_checkpoint_and_metrics_files_written(self) -> None:
        settings = Settings(
            source="chesscom",
            duckdb_path=self.tmp_dir / "tactix_chesscom.duckdb",
            checkpoint_path=self.tmp_dir / "since_lichess.txt",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_chesscom.txt",
            fixture_pgn_path=self.chesscom_fixture_path,
            chesscom_fixture_pgn_path=self.chesscom_fixture_path,
            chesscom_use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        )

        result = run_daily_game_sync(settings)

        self.assertGreater(result["metrics_version"], 0)
        self.assertTrue(settings.metrics_version_file.exists())
        self.assertEqual(
            int(settings.metrics_version_file.read_text().strip()),
            result["metrics_version"],
        )

        cursor = read_cursor(settings.checkpoint_path)
        self.assertIsNotNone(cursor)
        self.assertGreater(len(cursor or ""), 0)

    def test_incremental_run_skips_existing_games(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint.json",
            fixture_pgn_path=self.fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        first = run_daily_game_sync(settings)
        conn = get_connection(settings.duckdb_path)
        raw_first = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_first = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_first = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_first = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        metrics_version_first = fetch_version(conn)
        checkpoint_first = read_checkpoint(settings.checkpoint_path)

        self.assertGreater(first["fetched_games"], 0)
        self.assertGreater(checkpoint_first, 0)
        self.assertEqual(tactics_first, outcomes_first)

        second = run_daily_game_sync(settings)
        raw_second = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_second = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_second = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_second = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        metrics_version_second = fetch_version(conn)
        checkpoint_second = read_checkpoint(settings.checkpoint_path)
        conn.close()

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(raw_second, raw_first)
        self.assertEqual(positions_second, positions_first)
        self.assertEqual(tactics_second, tactics_first)
        self.assertEqual(outcomes_second, outcomes_first)
        self.assertEqual(checkpoint_second, checkpoint_first)
        self.assertEqual(metrics_version_second, metrics_version_first + 1)

    def test_chesscom_incremental_run_skips_existing_games(self) -> None:
        settings = Settings(
            source="chesscom",
            duckdb_path=self.tmp_dir / "tactix_chesscom.duckdb",
            checkpoint_path=self.tmp_dir / "since_lichess.txt",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_chesscom.txt",
            fixture_pgn_path=self.chesscom_fixture_path,
            chesscom_fixture_pgn_path=self.chesscom_fixture_path,
            chesscom_use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        first = run_daily_game_sync(settings)
        conn = get_connection(settings.duckdb_path)
        raw_first = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_first = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_first = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_first = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        metrics_version_first = fetch_version(conn)
        cursor_first = read_cursor(settings.checkpoint_path)

        self.assertGreater(first["fetched_games"], 0)
        self.assertGreater(len(cursor_first or ""), 0)
        self.assertEqual(tactics_first, outcomes_first)

        second = run_daily_game_sync(settings)
        raw_second = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_second = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_second = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_second = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        metrics_version_second = fetch_version(conn)
        cursor_second = read_cursor(settings.checkpoint_path)
        conn.close()

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(raw_second, raw_first)
        self.assertEqual(positions_second, positions_first)
        self.assertEqual(tactics_second, tactics_first)
        self.assertEqual(outcomes_second, outcomes_first)
        self.assertEqual(cursor_second, cursor_first)
        self.assertEqual(metrics_version_second, metrics_version_first + 1)

    def test_resume_after_partial_failure_and_dedup(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            fixture_pgn_path=self.fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        failure_called = {"count": 0}
        from tactix.pipeline import _analyse_with_retries as real_analyse

        def fail_once_analyze(engine, pos, settings):
            failure_called["count"] += 1
            if failure_called["count"] == 3:
                raise RuntimeError("simulated analysis failure")
            return real_analyse(engine, pos, settings)

        with patch(
            "tactix.pipeline._analyse_with_retries", side_effect=fail_once_analyze
        ):
            with self.assertRaises(RuntimeError):
                run_daily_game_sync(settings)

        self.assertEqual(read_checkpoint(settings.checkpoint_path), 0)
        self.assertFalse(settings.metrics_version_file.exists())
        self.assertTrue(settings.analysis_checkpoint_path.exists())

        conn = get_connection(settings.duckdb_path)
        raw_after_failure = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_after_failure = conn.execute(
            "SELECT COUNT(*) FROM positions"
        ).fetchone()[0]
        tactics_after_failure = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[
            0
        ]
        conn.close()

        self.assertGreater(raw_after_failure, 0)
        self.assertGreater(positions_after_failure, 0)
        self.assertGreater(tactics_after_failure, 0)
        self.assertLess(tactics_after_failure, positions_after_failure)

        result = run_daily_game_sync(settings)
        conn = get_connection(settings.duckdb_path)
        raw_after_recovery = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_after_recovery = conn.execute(
            "SELECT COUNT(*) FROM positions"
        ).fetchone()[0]
        tactics_after_recovery = conn.execute(
            "SELECT COUNT(*) FROM tactics"
        ).fetchone()[0]
        outcomes_after_recovery = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        metrics_version_after = fetch_version(conn)
        conn.close()

        self.assertEqual(raw_after_recovery, raw_after_failure)
        self.assertEqual(positions_after_recovery, positions_after_failure)
        self.assertEqual(tactics_after_recovery, outcomes_after_recovery)
        self.assertGreater(result["checkpoint_ms"], 0)
        self.assertEqual(
            read_checkpoint(settings.checkpoint_path), result["checkpoint_ms"]
        )
        self.assertTrue(settings.metrics_version_file.exists())
        self.assertGreater(metrics_version_after, 0)
        self.assertFalse(settings.analysis_checkpoint_path.exists())

    def test_resume_after_stockfish_crash(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint.json",
            fixture_pgn_path=self.fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
            stockfish_max_retries=0,
        )

        call_count = {"count": 0}
        from tactix.stockfish_runner import StockfishEngine

        original_analyse = StockfishEngine.analyse

        def crash_once(self, board):
            call_count["count"] += 1
            if call_count["count"] == 4:
                raise chess.engine.EngineTerminatedError("simulated crash")
            return original_analyse(self, board)

        with patch("tactix.stockfish_runner.StockfishEngine.analyse", new=crash_once):
            with self.assertRaises(chess.engine.EngineTerminatedError):
                run_daily_game_sync(settings)

        self.assertTrue(settings.analysis_checkpoint_path.exists())

        conn = get_connection(settings.duckdb_path)
        tactics_after_failure = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[
            0
        ]
        positions_after_failure = conn.execute(
            "SELECT COUNT(*) FROM positions"
        ).fetchone()[0]
        conn.close()
        self.assertGreater(tactics_after_failure, 0)
        self.assertLess(tactics_after_failure, positions_after_failure)

        result = run_daily_game_sync(settings)
        conn = get_connection(settings.duckdb_path)
        tactics_after_recovery = conn.execute(
            "SELECT COUNT(*) FROM tactics"
        ).fetchone()[0]
        outcomes_after_recovery = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(tactics_after_recovery, outcomes_after_recovery)
        self.assertGreater(result["checkpoint_ms"], 0)
        self.assertFalse(settings.analysis_checkpoint_path.exists())

    def test_fetch_failure_does_not_advance_checkpoint(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            fixture_pgn_path=self.fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        with patch(
            "tactix.pipeline.fetch_lichess_games",
            side_effect=RuntimeError("network down"),
        ):
            with self.assertRaises(RuntimeError):
                run_daily_game_sync(settings)

        self.assertEqual(read_checkpoint(settings.checkpoint_path), 0)
        self.assertFalse(settings.metrics_version_file.exists())

        result = run_daily_game_sync(settings)
        self.assertGreater(result["checkpoint_ms"], 0)
        self.assertTrue(settings.metrics_version_file.exists())


if __name__ == "__main__":
    unittest.main()
