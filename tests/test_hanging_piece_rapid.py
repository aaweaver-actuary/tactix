import shutil
import tempfile
import unittest
from pathlib import Path

from tactix.config import DEFAULT_RAPID_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import (
    get_connection,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position
from tests.fixture_helpers import (
    find_failed_attempt_position,
    find_missed_position,
    hanging_piece_fixture_position,
    hanging_piece_high_fixture_position,
)


class HangingPieceRapidTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_rapid_hanging_piece_is_low_severity(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="rapid",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("rapid")
        self.assertEqual(settings.stockfish_depth, DEFAULT_RAPID_STOCKFISH_DEPTH)

        position = hanging_piece_fixture_position(
            fixture_filename="chesscom_rapid_sample.pgn",
            label="Rapid Fixture 11 - Hanging Piece Low",
            game_id="rapid-hanging-piece-low",
        )

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "hanging_piece_rapid.duckdb")
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
    def test_rapid_hanging_piece_is_high_severity(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="rapid",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=120,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("rapid")
        self.assertEqual(settings.stockfish_depth, DEFAULT_RAPID_STOCKFISH_DEPTH)

        position = hanging_piece_high_fixture_position(
            fixture_filename="chesscom_rapid_sample.pgn",
            label="Rapid Fixture 12 - Hanging Piece High",
            game_id="rapid-hanging-piece-high",
        )

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "hanging_piece_rapid_high.duckdb")
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

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_rapid_hanging_piece_records_found_outcome(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="rapid",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("rapid")

        position = hanging_piece_fixture_position(
            fixture_filename="chesscom_rapid_sample.pgn",
            label="Rapid Fixture 11 - Hanging Piece Low",
            game_id="rapid-hanging-piece-low",
        )

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "hanging_piece_rapid_found.duckdb")
        init_schema(conn)

        with StockfishEngine(settings) as engine:
            result = analyze_position(position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        if outcome_row["result"] != "found" and tactic_row.get("best_uci"):
            position["uci"] = tactic_row["best_uci"]
            try:
                board = chess.Board(str(position["fen"]))
                move = chess.Move.from_uci(position["uci"])
                position["san"] = board.san(move)
            except Exception:
                pass
            with StockfishEngine(settings) as engine:
                result = analyze_position(position, engine, settings=settings)
            self.assertIsNotNone(result)
            tactic_row, outcome_row = result

        self.assertEqual(tactic_row["motif"], "hanging_piece")
        self.assertEqual(outcome_row["result"], "found")

        position_ids = insert_positions(conn, [position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "found")
        self.assertEqual(stored_outcome[1], position["uci"])

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_rapid_hanging_piece_records_missed_outcome(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="rapid",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("rapid")

        position = hanging_piece_fixture_position(
            fixture_filename="chesscom_rapid_sample.pgn",
            label="Rapid Fixture 11 - Hanging Piece Low",
            game_id="rapid-hanging-piece-low",
        )

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "hanging_piece_rapid_missed.duckdb")
        init_schema(conn)

        with StockfishEngine(settings) as engine:
            missed_position, result = find_missed_position(
                position, engine, settings, "hanging_piece"
            )

        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "hanging_piece")
        self.assertEqual(outcome_row["result"], "missed")

        position_ids = insert_positions(conn, [missed_position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "missed")
        self.assertEqual(stored_outcome[1], missed_position["uci"])

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_rapid_hanging_piece_records_failed_attempt_outcome(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="rapid",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("rapid")

        position = hanging_piece_fixture_position(
            fixture_filename="chesscom_rapid_sample.pgn",
            label="Rapid Fixture 11 - Hanging Piece Low",
            game_id="rapid-hanging-piece-low",
        )

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "hanging_piece_rapid_failed_attempt.duckdb")
        init_schema(conn)

        with StockfishEngine(settings) as engine:
            failed_position, result = find_failed_attempt_position(
                position, engine, settings, "hanging_piece"
            )

        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "hanging_piece")
        self.assertEqual(outcome_row["result"], "failed_attempt")
        self.assertTrue(tactic_row["best_uci"])
        self.assertNotEqual(tactic_row["best_uci"], failed_position["uci"])

        position_ids = insert_positions(conn, [failed_position])
        tactic_row["position_id"] = position_ids[0]

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "failed_attempt")
        self.assertEqual(stored_outcome[1], failed_position["uci"])


if __name__ == "__main__":
    unittest.main()
