import shutil
import tempfile
import unittest
from pathlib import Path

from tactix.config import DEFAULT_CLASSICAL_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)
from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from tests.fixture_helpers import (
    hanging_piece_fixture_position,
    hanging_piece_high_fixture_position,
)


class HangingPieceClassicalTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_classical_hanging_piece_is_low_severity(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="classical",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("classical")
        self.assertEqual(settings.stockfish_depth, DEFAULT_CLASSICAL_STOCKFISH_DEPTH)

        position = hanging_piece_fixture_position(
            fixture_filename="chesscom_classical_sample.pgn",
            label="Classical Fixture 11 - Hanging Piece Low",
            game_id="classical-hanging-piece-low",
        )

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "hanging_piece_classical.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "hanging_piece")
        self.assertGreater(tactic_row["severity"], 0)
        self.assertLessEqual(tactic_row["severity"], 1.0)
        self.assertTrue(tactic_row["best_uci"])

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored = conn.execute(
            "SELECT position_id, best_san, explanation FROM tactics WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored[0], position_ids[0])
        self.assertIsNotNone(stored[1])
        self.assertIn("Best line", stored[2] or "")

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_classical_hanging_piece_is_high_severity(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="classical",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=180,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("classical")
        self.assertEqual(settings.stockfish_depth, DEFAULT_CLASSICAL_STOCKFISH_DEPTH)

        position = hanging_piece_high_fixture_position(
            fixture_filename="chesscom_classical_sample.pgn",
            label="Classical Fixture 12 - Hanging Piece High",
            game_id="classical-hanging-piece-high",
        )

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "hanging_piece_classical_high.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "hanging_piece")
        self.assertGreaterEqual(tactic_row["severity"], 1.5)
        self.assertTrue(tactic_row["best_uci"])

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored = conn.execute(
            "SELECT position_id, best_san, explanation FROM tactics WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored[0], position_ids[0])
        self.assertIsNotNone(stored[1])
        self.assertIn("Best line", stored[2] or "")


if __name__ == "__main__":
    unittest.main()
