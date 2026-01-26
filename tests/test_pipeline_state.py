import shutil
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import chess.engine

from tactix.config import Settings
from tactix.duckdb_store import fetch_version, get_connection
from tactix.pgn_utils import extract_last_timestamp_ms, split_pgn_chunks
from tactix.lichess_client import read_checkpoint
from tactix.chesscom_client import read_cursor
from tactix.pipeline import run_daily_game_sync


class PipelineStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
        )
        self.bullet_fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_bullet_sample.pgn"
        )
        self.blitz_fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_blitz_sample.pgn"
        )
        self.classical_fixture_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "lichess_classical_sample.pgn"
        )
        self.correspondence_fixture_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "lichess_correspondence_sample.pgn"
        )
        self.chesscom_fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_blitz_sample.pgn"
        )
        self.chesscom_bullet_fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_bullet_sample.pgn"
        )
        self.chesscom_rapid_fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_rapid_sample.pgn"
        )
        self.chesscom_classical_fixture_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "chesscom_classical_sample.pgn"
        )
        self.chesscom_correspondence_fixture_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "chesscom_correspondence_sample.pgn"
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

    def test_chesscom_bullet_incremental_sync_uses_profile_checkpoint(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_profile="bullet",
            duckdb_path=self.tmp_dir / "tactix_chesscom_bullet.duckdb",
            checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_chesscom.txt",
            fixture_pgn_path=self.chesscom_bullet_fixture_path,
            chesscom_fixture_pgn_path=self.chesscom_bullet_fixture_path,
            chesscom_use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        first = run_daily_game_sync(settings, profile="bullet")
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_bullet.txt")
        )
        cursor_first = read_cursor(settings.checkpoint_path)
        self.assertIsNotNone(cursor_first)

        second = run_daily_game_sync(settings, profile="bullet")
        cursor_second = read_cursor(settings.checkpoint_path)

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(cursor_second, cursor_first)

    def test_chesscom_blitz_incremental_sync_uses_profile_checkpoint(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_profile="blitz",
            duckdb_path=self.tmp_dir / "tactix_chesscom_blitz.duckdb",
            checkpoint_path=self.tmp_dir / "chesscom_since.txt",
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

        first = run_daily_game_sync(settings, profile="blitz")
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_blitz.txt")
        )
        self.assertEqual(
            settings.chesscom_fixture_pgn_path.name, "chesscom_blitz_sample.pgn"
        )
        cursor_first = read_cursor(settings.checkpoint_path)
        self.assertIsNotNone(cursor_first)

        second = run_daily_game_sync(settings, profile="blitz")
        cursor_second = read_cursor(settings.checkpoint_path)

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(cursor_second, cursor_first)

    def test_chesscom_rapid_incremental_sync_uses_profile_checkpoint(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_profile="rapid",
            duckdb_path=self.tmp_dir / "tactix_chesscom_rapid.duckdb",
            checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_chesscom.txt",
            fixture_pgn_path=self.chesscom_rapid_fixture_path,
            chesscom_fixture_pgn_path=self.chesscom_rapid_fixture_path,
            chesscom_use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        first = run_daily_game_sync(settings, profile="rapid")
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_rapid.txt")
        )
        self.assertEqual(
            settings.chesscom_fixture_pgn_path.name, "chesscom_rapid_sample.pgn"
        )
        cursor_first = read_cursor(settings.checkpoint_path)
        self.assertIsNotNone(cursor_first)

        second = run_daily_game_sync(settings, profile="rapid")
        cursor_second = read_cursor(settings.checkpoint_path)

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(cursor_second, cursor_first)

    def test_chesscom_classical_incremental_sync_uses_profile_checkpoint(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_profile="classical",
            duckdb_path=self.tmp_dir / "tactix_chesscom_classical.duckdb",
            checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_chesscom.txt",
            fixture_pgn_path=self.chesscom_classical_fixture_path,
            chesscom_fixture_pgn_path=self.chesscom_classical_fixture_path,
            chesscom_use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        first = run_daily_game_sync(settings, profile="classical")
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_classical.txt")
        )
        self.assertEqual(
            settings.chesscom_fixture_pgn_path.name, "chesscom_classical_sample.pgn"
        )
        cursor_first = read_cursor(settings.checkpoint_path)
        self.assertIsNotNone(cursor_first)

        second = run_daily_game_sync(settings, profile="classical")
        cursor_second = read_cursor(settings.checkpoint_path)

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(cursor_second, cursor_first)

    def test_chesscom_correspondence_incremental_sync_uses_profile_checkpoint(
        self,
    ) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_profile="correspondence",
            duckdb_path=self.tmp_dir / "tactix_chesscom_correspondence.duckdb",
            checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_chesscom.txt",
            fixture_pgn_path=self.chesscom_correspondence_fixture_path,
            chesscom_fixture_pgn_path=self.chesscom_correspondence_fixture_path,
            chesscom_use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        first = run_daily_game_sync(settings, profile="correspondence")
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_correspondence.txt")
        )
        self.assertEqual(
            settings.chesscom_fixture_pgn_path.name,
            "chesscom_correspondence_sample.pgn",
        )
        cursor_first = read_cursor(settings.checkpoint_path)
        self.assertIsNotNone(cursor_first)

        second = run_daily_game_sync(settings, profile="correspondence")
        cursor_second = read_cursor(settings.checkpoint_path)

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(cursor_second, cursor_first)

    def test_chesscom_bullet_backfill_window_is_idempotent(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_profile="bullet",
            duckdb_path=self.tmp_dir / "tactix_chesscom_bullet.duckdb",
            checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_chesscom_bullet.txt",
            chesscom_use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        pgn_text = self.chesscom_bullet_fixture_path.read_text()
        timestamps = [
            extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)
        ]
        window_start = min(timestamps) - 1000
        window_end = max(timestamps) + 1000

        first = run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="bullet",
        )
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_bullet.txt")
        )
        self.assertEqual(
            settings.chesscom_fixture_pgn_path.name, "chesscom_bullet_sample.pgn"
        )
        cursor_after_first = read_cursor(settings.checkpoint_path)
        self.assertIsNone(cursor_after_first)

        conn = get_connection(settings.duckdb_path)
        raw_before = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_before = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_before = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_before = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="bullet",
        )

        conn = get_connection(settings.duckdb_path)
        raw_after = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_after = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_after = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_after = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(raw_after, raw_before)
        self.assertEqual(positions_after, positions_before)
        self.assertEqual(tactics_after, tactics_before)
        self.assertEqual(outcomes_after, outcomes_before)

    def test_chesscom_blitz_backfill_window_is_idempotent(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_profile="blitz",
            duckdb_path=self.tmp_dir / "tactix_chesscom_blitz_backfill.duckdb",
            checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_chesscom_blitz.txt",
            fixture_pgn_path=self.chesscom_bullet_fixture_path,
            chesscom_fixture_pgn_path=self.chesscom_bullet_fixture_path,
            chesscom_use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        pgn_text = self.chesscom_fixture_path.read_text()
        timestamps = [
            extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)
        ]
        window_start = min(timestamps) - 1000
        window_end = max(timestamps) + 1000

        first = run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="blitz",
        )
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_blitz.txt")
        )
        self.assertEqual(
            settings.chesscom_fixture_pgn_path.name, "chesscom_blitz_sample.pgn"
        )
        self.assertEqual(settings.fixture_pgn_path.name, "chesscom_blitz_sample.pgn")
        cursor_after_first = read_cursor(settings.checkpoint_path)
        self.assertIsNone(cursor_after_first)

        conn = get_connection(settings.duckdb_path)
        raw_before = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_before = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_before = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_before = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="blitz",
        )

        conn = get_connection(settings.duckdb_path)
        raw_after = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_after = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_after = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_after = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(raw_after, raw_before)
        self.assertEqual(positions_after, positions_before)
        self.assertEqual(tactics_after, tactics_before)
        self.assertEqual(outcomes_after, outcomes_before)

    def test_chesscom_classical_backfill_window_is_idempotent(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_profile="classical",
            duckdb_path=self.tmp_dir / "tactix_chesscom_classical_backfill.duckdb",
            checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_chesscom_classical.txt",
            fixture_pgn_path=self.chesscom_classical_fixture_path,
            chesscom_fixture_pgn_path=self.chesscom_classical_fixture_path,
            chesscom_use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        pgn_text = self.chesscom_classical_fixture_path.read_text()
        timestamps = [
            extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)
        ]
        window_start = min(timestamps) - 1000
        window_end = max(timestamps) + 1000

        first = run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="classical",
        )
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("chesscom_since_classical.txt")
        )
        self.assertEqual(
            settings.chesscom_fixture_pgn_path.name, "chesscom_classical_sample.pgn"
        )
        self.assertEqual(
            settings.fixture_pgn_path.name, "chesscom_classical_sample.pgn"
        )
        cursor_after_first = read_cursor(settings.checkpoint_path)
        self.assertIsNone(cursor_after_first)

        conn = get_connection(settings.duckdb_path)
        raw_before = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_before = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_before = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_before = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="classical",
        )

        conn = get_connection(settings.duckdb_path)
        raw_after = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_after = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_after = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_after = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(raw_after, raw_before)
        self.assertEqual(positions_after, positions_before)
        self.assertEqual(tactics_after, tactics_before)
        self.assertEqual(outcomes_after, outcomes_before)

    def test_incremental_run_skips_existing_games(self) -> None:
        settings = Settings(
            user="andy_andy_andy",
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

    def test_lichess_rapid_incremental_sync_uses_profile_checkpoint(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix_rapid.duckdb",
            checkpoint_path=self.tmp_dir / "lichess_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_rapid.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint_lichess.json",
            fixture_pgn_path=self.fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
            lichess_profile="rapid",
        )

        first = run_daily_game_sync(settings, profile="rapid")
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_rapid.txt")
        )
        checkpoint_first = read_checkpoint(settings.checkpoint_path)
        self.assertGreater(checkpoint_first, 0)

        second = run_daily_game_sync(settings, profile="rapid")
        checkpoint_second = read_checkpoint(settings.checkpoint_path)

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(checkpoint_second, checkpoint_first)

    def test_lichess_classical_incremental_sync_uses_profile_checkpoint(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix_classical.duckdb",
            checkpoint_path=self.tmp_dir / "lichess_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_classical.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint_lichess.json",
            fixture_pgn_path=self.classical_fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
            lichess_profile="classical",
        )

        first = run_daily_game_sync(settings, profile="classical")
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_classical.txt")
        )
        checkpoint_first = read_checkpoint(settings.checkpoint_path)
        self.assertGreater(checkpoint_first, 0)

        second = run_daily_game_sync(settings, profile="classical")
        checkpoint_second = read_checkpoint(settings.checkpoint_path)

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(checkpoint_second, checkpoint_first)

    def test_lichess_correspondence_incremental_sync_uses_profile_checkpoint(
        self,
    ) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix_correspondence.duckdb",
            checkpoint_path=self.tmp_dir / "lichess_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_correspondence.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint_lichess.json",
            fixture_pgn_path=self.correspondence_fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
            lichess_profile="correspondence",
        )

        first = run_daily_game_sync(settings, profile="correspondence")
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_correspondence.txt")
        )
        checkpoint_first = read_checkpoint(settings.checkpoint_path)
        self.assertGreater(checkpoint_first, 0)

        second = run_daily_game_sync(settings, profile="correspondence")
        checkpoint_second = read_checkpoint(settings.checkpoint_path)

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(checkpoint_second, checkpoint_first)

    def test_lichess_correspondence_backfill_window_is_idempotent(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix_correspondence.duckdb",
            checkpoint_path=self.tmp_dir / "lichess_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_correspondence.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint_lichess.json",
            fixture_pgn_path=self.correspondence_fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
            lichess_profile="correspondence",
        )

        pgn_text = self.correspondence_fixture_path.read_text()
        timestamps = [
            extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)
        ]
        window_start = min(timestamps) - 1000
        window_end = max(timestamps) + 1000

        first = run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="correspondence",
        )
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_correspondence.txt")
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("lichess_correspondence_sample.pgn")
        )
        checkpoint_after_first = read_checkpoint(settings.checkpoint_path)
        self.assertEqual(checkpoint_after_first, 0)

        conn = get_connection(settings.duckdb_path)
        raw_before = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_before = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_before = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_before = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="correspondence",
        )

        conn = get_connection(settings.duckdb_path)
        raw_after = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_after = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_after = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_after = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(raw_after, raw_before)
        self.assertEqual(positions_after, positions_before)
        self.assertEqual(tactics_after, tactics_before)
        self.assertEqual(outcomes_after, outcomes_before)

    def test_lichess_classical_backfill_window_is_idempotent(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix_classical.duckdb",
            checkpoint_path=self.tmp_dir / "lichess_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_classical.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint_lichess.json",
            fixture_pgn_path=self.classical_fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
            lichess_profile="classical",
        )

        pgn_text = self.classical_fixture_path.read_text()
        timestamps = [
            extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)
        ]
        window_start = min(timestamps) - 1000
        window_end = max(timestamps) + 1000

        first = run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="classical",
        )
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_classical.txt")
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("lichess_classical_sample.pgn")
        )
        checkpoint_after_first = read_checkpoint(settings.checkpoint_path)
        self.assertEqual(checkpoint_after_first, 0)

        conn = get_connection(settings.duckdb_path)
        raw_before = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_before = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_before = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_before = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="classical",
        )

        conn = get_connection(settings.duckdb_path)
        raw_after = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_after = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_after = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_after = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(raw_after, raw_before)
        self.assertEqual(positions_after, positions_before)
        self.assertEqual(tactics_after, tactics_before)
        self.assertEqual(outcomes_after, outcomes_before)

    def test_lichess_rapid_backfill_window_is_idempotent(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix_rapid.duckdb",
            checkpoint_path=self.tmp_dir / "lichess_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_rapid.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint_lichess.json",
            fixture_pgn_path=self.fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
            lichess_profile="rapid",
        )

        pgn_text = self.fixture_path.read_text()
        timestamps = [
            extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)
        ]
        window_start = min(timestamps) - 1000
        window_end = max(timestamps) + 1000

        first = run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="rapid",
        )
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_rapid.txt")
        )
        self.assertTrue(
            settings.fixture_pgn_path.name.endswith("lichess_rapid_sample.pgn")
        )
        checkpoint_after_first = read_checkpoint(settings.checkpoint_path)
        self.assertEqual(checkpoint_after_first, 0)

        conn = get_connection(settings.duckdb_path)
        raw_before = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_before = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_before = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_before = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="rapid",
        )

        conn = get_connection(settings.duckdb_path)
        raw_after = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_after = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_after = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_after = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(raw_after, raw_before)
        self.assertEqual(positions_after, positions_before)
        self.assertEqual(tactics_after, tactics_before)
        self.assertEqual(outcomes_after, outcomes_before)

    def test_lichess_bullet_incremental_sync_uses_profile_checkpoint(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix_bullet.duckdb",
            checkpoint_path=self.tmp_dir / "lichess_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_bullet.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint_lichess.json",
            fixture_pgn_path=self.bullet_fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
            lichess_profile="bullet",
        )

        first = run_daily_game_sync(settings, profile="bullet")
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_bullet.txt")
        )
        checkpoint_first = read_checkpoint(settings.checkpoint_path)
        self.assertGreater(checkpoint_first, 0)

        second = run_daily_game_sync(settings, profile="bullet")
        checkpoint_second = read_checkpoint(settings.checkpoint_path)

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(checkpoint_second, checkpoint_first)

    def test_lichess_bullet_backfill_window_is_idempotent(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix_bullet.duckdb",
            checkpoint_path=self.tmp_dir / "lichess_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_bullet.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint_lichess.json",
            fixture_pgn_path=self.bullet_fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
            lichess_profile="bullet",
        )

        pgn_text = self.bullet_fixture_path.read_text()
        timestamps = [
            extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)
        ]
        window_start = min(timestamps) - 1000
        window_end = max(timestamps) + 1000

        first = run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="bullet",
        )
        self.assertGreater(first["fetched_games"], 0)
        checkpoint_after_first = read_checkpoint(settings.checkpoint_path)
        self.assertEqual(checkpoint_after_first, 0)

        conn = get_connection(settings.duckdb_path)
        raw_before = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_before = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_before = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_before = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="bullet",
        )

        conn = get_connection(settings.duckdb_path)
        raw_after = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_after = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_after = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_after = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(raw_after, raw_before)
        self.assertEqual(positions_after, positions_before)
        self.assertEqual(tactics_after, tactics_before)
        self.assertEqual(outcomes_after, outcomes_before)

    def test_lichess_blitz_incremental_sync_uses_profile_checkpoint(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix_blitz.duckdb",
            checkpoint_path=self.tmp_dir / "lichess_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_blitz.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint_lichess.json",
            fixture_pgn_path=self.blitz_fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
            lichess_profile="blitz",
        )

        first = run_daily_game_sync(settings, profile="blitz")
        self.assertGreater(first["fetched_games"], 0)
        self.assertTrue(
            settings.checkpoint_path.name.endswith("lichess_since_blitz.txt")
        )
        checkpoint_first = read_checkpoint(settings.checkpoint_path)
        self.assertGreater(checkpoint_first, 0)

        second = run_daily_game_sync(settings, profile="blitz")
        checkpoint_second = read_checkpoint(settings.checkpoint_path)

        self.assertEqual(second["fetched_games"], 0)
        self.assertEqual(second["positions"], 0)
        self.assertEqual(second["tactics"], 0)
        self.assertEqual(checkpoint_second, checkpoint_first)

    def test_lichess_blitz_backfill_window_is_idempotent(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "tactix_blitz.duckdb",
            checkpoint_path=self.tmp_dir / "lichess_since.txt",
            metrics_version_file=self.tmp_dir / "metrics_blitz.txt",
            analysis_checkpoint_path=self.tmp_dir / "analysis_checkpoint_lichess.json",
            fixture_pgn_path=self.blitz_fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=50,
            stockfish_depth=8,
            stockfish_multipv=2,
            lichess_profile="blitz",
        )

        pgn_text = self.blitz_fixture_path.read_text()
        timestamps = [
            extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)
        ]
        window_start = min(timestamps) - 1000
        window_end = max(timestamps) + 1000

        first = run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="blitz",
        )
        self.assertGreater(first["fetched_games"], 0)
        checkpoint_after_first = read_checkpoint(settings.checkpoint_path)
        self.assertEqual(checkpoint_after_first, 0)

        conn = get_connection(settings.duckdb_path)
        raw_before = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_before = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_before = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_before = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        run_daily_game_sync(
            settings,
            window_start_ms=window_start,
            window_end_ms=window_end,
            profile="blitz",
        )

        conn = get_connection(settings.duckdb_path)
        raw_after = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_after = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_after = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_after = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(raw_after, raw_before)
        self.assertEqual(positions_after, positions_before)
        self.assertEqual(tactics_after, tactics_before)
        self.assertEqual(outcomes_after, outcomes_before)

    def test_backfill_replay_is_idempotent(self) -> None:
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

        run_daily_game_sync(settings)
        conn = get_connection(settings.duckdb_path)
        raw_before = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_before = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_before = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_before = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        checkpoint_before = read_checkpoint(settings.checkpoint_path)
        conn.close()

        pgn_text = self.fixture_path.read_text()
        timestamps = [
            extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)
        ]
        window_start = min(timestamps) - 1000
        window_end = max(timestamps) + 1000

        run_daily_game_sync(
            settings, window_start_ms=window_start, window_end_ms=window_end
        )
        run_daily_game_sync(
            settings, window_start_ms=window_start, window_end_ms=window_end
        )

        conn = get_connection(settings.duckdb_path)
        raw_after = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions_after = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics_after = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes_after = conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes"
        ).fetchone()[0]
        checkpoint_after = read_checkpoint(settings.checkpoint_path)
        conn.close()

        self.assertEqual(raw_after, raw_before)
        self.assertEqual(positions_after, positions_before)
        self.assertEqual(tactics_after, tactics_before)
        self.assertEqual(outcomes_after, outcomes_before)
        self.assertEqual(checkpoint_after, checkpoint_before)

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
