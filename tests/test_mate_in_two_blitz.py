import shutil
import tempfile
import unittest
from pathlib import Path

import chess

from tactix.config import DEFAULT_BLITZ_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import (
    get_connection,
    grade_practice_attempt,
    init_schema,
    insert_positions,
    upsert_tactic_with_outcome,
)
from tactix.pgn_utils import split_pgn_chunks
from tactix.position_extractor import extract_positions
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position
from tests.fixture_helpers import find_failed_attempt_position, find_missed_position
class MateInTwoBlitzTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_blitz_mate_in_two_is_high_severity(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_blitz_sample.pgn"
        )
        chunks = split_pgn_chunks(fixture_path.read_text())
        mate_pgn = next(chunk for chunk in chunks if "Blitz Fixture 4" in chunk)

        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="blitz",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("blitz")
        self.assertEqual(settings.stockfish_depth, DEFAULT_BLITZ_STOCKFISH_DEPTH)

        positions = extract_positions(
            mate_pgn,
            settings.chesscom_user,
            settings.source,
            game_id="blitz-mate-2",
            side_to_move_filter="black",
        )
        mate_position = next(pos for pos in positions if pos["uci"] == "c5f2")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "mate_in_two_blitz.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [mate_position])
        mate_position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(mate_position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertEqual(tactic_row["best_uci"], "c5f2")
        self.assertGreaterEqual(tactic_row["severity"], 1.5)
        self.assertLessEqual(abs(outcome_row["eval_delta"]), 100)
        self.assertEqual(outcome_row["result"], "found")

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored_position_id = conn.execute(
            "SELECT position_id FROM tactics WHERE tactic_id = ?", [tactic_id]
        ).fetchone()[0]
        self.assertEqual(stored_position_id, position_ids[0])
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "found")
        self.assertEqual(stored_outcome[1], "c5f2")

        stored_line = conn.execute(
            "SELECT best_san, explanation FROM tactics WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertIsNotNone(stored_line[0])
        self.assertIn("Best line", stored_line[1] or "")

        attempt = grade_practice_attempt(conn, tactic_id, position_ids[0], "c5f2")
        self.assertIn("Best line", attempt["explanation"] or "")
        self.assertIn("f2", attempt["explanation"] or "")

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_blitz_mate_in_two_records_missed_outcome(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_blitz_sample.pgn"
        )
        chunks = split_pgn_chunks(fixture_path.read_text())
        mate_pgn = next(chunk for chunk in chunks if "Blitz Fixture 4" in chunk)

        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="blitz",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("blitz")

        positions = extract_positions(
            mate_pgn,
            settings.chesscom_user,
            settings.source,
            game_id="blitz-mate-2",
            side_to_move_filter="black",
        )
        mate_position = next(pos for pos in positions if pos["uci"] == "c5f2")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "mate_in_two_blitz_missed.duckdb")
        init_schema(conn)

        with StockfishEngine(settings) as engine:
            missed_position, result = find_missed_position(
                mate_position, engine, settings, "mate"
            )

        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
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
    def test_blitz_mate_in_two_records_failed_attempt_outcome(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_blitz_sample.pgn"
        )
        chunks = split_pgn_chunks(fixture_path.read_text())
        mate_pgn = next(chunk for chunk in chunks if "Blitz Fixture 4" in chunk)

        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="blitz",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("blitz")

        positions = extract_positions(
            mate_pgn,
            settings.chesscom_user,
            settings.source,
            game_id="blitz-mate-2",
            side_to_move_filter="black",
        )
        mate_position = next(pos for pos in positions if pos["uci"] == "c5f2")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "mate_in_two_blitz_failed_attempt.duckdb")
        init_schema(conn)

        with StockfishEngine(settings) as engine:
            failed_position, result = find_failed_attempt_position(
                mate_position, engine, settings, "mate"
            )

        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertEqual(outcome_row["result"], "failed_attempt")

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
