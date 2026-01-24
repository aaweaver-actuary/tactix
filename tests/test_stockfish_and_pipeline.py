import shutil
import tempfile
from pathlib import Path
import unittest

import chess

from tactix.config import Settings
from tactix.duckdb_store import (
    get_connection,
    fetch_metrics,
    fetch_recent_positions,
    fetch_recent_tactics,
)
from tactix.pipeline import run_daily_game_sync
from tactix.stockfish_runner import StockfishEngine


class StockfishAndPipelineTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_stockfish_is_deterministic(self) -> None:
        settings = Settings(
            stockfish_path=Path("stockfish"),
            stockfish_movetime_ms=80,
            stockfish_depth=10,
            stockfish_threads=1,
            stockfish_multipv=2,
        )
        board = chess.Board()
        with StockfishEngine(settings) as engine:
            first = engine.analyse(board)
            second = engine.analyse(board)
        self.assertEqual(first.best_move, second.best_move)
        self.assertEqual(first.score_cp, second.score_cp)

    def test_pipeline_writes_duckdb_tables(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
        )
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=tmp_dir / "tactix.duckdb",
            checkpoint_path=tmp_dir / "since.txt",
            metrics_version_file=tmp_dir / "metrics.txt",
            fixture_pgn_path=fixture_path,
            use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        result = run_daily_game_sync(settings)
        self.assertGreaterEqual(result["fetched_games"], 2)
        self.assertGreater(result["positions"], 0)
        self.assertGreater(result["tactics"], 0)
        self.assertGreater(result["metrics_version"], 0)

        conn = get_connection(settings.duckdb_path)
        raw_pgns = conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        positions = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        tactics = conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
        outcomes = conn.execute("SELECT COUNT(*) FROM tactic_outcomes").fetchone()[0]

        self.assertEqual(tactics, outcomes)
        self.assertGreaterEqual(raw_pgns, 2)
        self.assertGreaterEqual(positions, result["positions"])

        metrics = fetch_metrics(conn)
        self.assertGreaterEqual(len(metrics), 1)
        recent_positions = fetch_recent_positions(conn, limit=5)
        recent_tactics = fetch_recent_tactics(conn, limit=5)
        self.assertGreaterEqual(len(recent_positions), 1)
        self.assertGreaterEqual(len(recent_tactics), 1)

    def test_chesscom_pipeline_writes_duckdb_tables(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_blitz_sample.pgn"
        )
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            duckdb_path=tmp_dir / "tactix_chesscom.duckdb",
            chesscom_checkpoint_path=tmp_dir / "chesscom_since.txt",
            metrics_version_file=tmp_dir / "metrics_chesscom.txt",
            chesscom_fixture_pgn_path=fixture_path,
            chesscom_use_fixture_when_no_token=True,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=8,
            stockfish_multipv=2,
        )

        result = run_daily_game_sync(settings)
        self.assertEqual(result["source"], "chesscom")
        self.assertGreaterEqual(result["fetched_games"], 2)
        self.assertGreater(result["positions"], 0)
        self.assertGreater(result["tactics"], 0)

        conn = get_connection(settings.duckdb_path)
        raw_pgns = conn.execute("SELECT source, COUNT(*) FROM raw_pgns GROUP BY source").fetchall()
        self.assertIn(("chesscom", 2), raw_pgns)
        positions = conn.execute("SELECT COUNT(*) FROM positions WHERE source='chesscom'").fetchone()[0]
        tactics = conn.execute(
            "SELECT COUNT(*) FROM tactics t JOIN positions p ON p.position_id = t.position_id WHERE p.source='chesscom'"
        ).fetchone()[0]
        outcomes = conn.execute("SELECT COUNT(*) FROM tactic_outcomes").fetchone()[0]

        self.assertEqual(tactics, outcomes)
        self.assertGreaterEqual(positions, result["positions"])

        metrics = fetch_metrics(conn, source="chesscom")
        self.assertGreaterEqual(len(metrics), 1)
        recent_positions = fetch_recent_positions(conn, limit=5, source="chesscom")
        recent_tactics = fetch_recent_tactics(conn, limit=5, source="chesscom")
        self.assertGreaterEqual(len(recent_positions), 1)
        self.assertGreaterEqual(len(recent_tactics), 1)


if __name__ == "__main__":
    unittest.main()
