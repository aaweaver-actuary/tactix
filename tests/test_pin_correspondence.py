import shutil
import tempfile
import unittest
from pathlib import Path

from tactix.config import DEFAULT_CORRESPONDENCE_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from tests.fixture_helpers import (
    find_failed_attempt_position,
    find_missed_position,
    pin_fixture_position,
    pin_fixture_positions,
)


class PinCorrespondenceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_correspondence_pin_is_high_severity(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="correspondence",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("correspondence")
        self.assertEqual(settings.stockfish_depth, DEFAULT_CORRESPONDENCE_STOCKFISH_DEPTH)

        position = pin_fixture_position()

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "pin_correspondence.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "pin")
        self.assertGreater(tactic_row["severity"], 0)
        self.assertGreaterEqual(tactic_row["severity"], 1.5)
        self.assertIsNotNone(outcome_row["eval_delta"])
        self.assertEqual(outcome_row["result"], "found")

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored = conn.execute(
            "SELECT position_id, best_san, explanation FROM tactics WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored[0], position_ids[0])
        self.assertIsNotNone(stored[1])
        self.assertIn("Best line", stored[2] or "")
        stored_outcome = conn.execute(
            "SELECT result, user_uci FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored_outcome[0], "found")
        self.assertEqual(stored_outcome[1], position["uci"])

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_correspondence_pin_records_missed_outcome(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="correspondence",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("correspondence")

        positions = pin_fixture_positions()

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "pin_correspondence_missed.duckdb")
        init_schema(conn)

        missed_position = None
        result = None
        with StockfishEngine(settings) as engine:
            for position in positions:
                try:
                    missed_position, result = find_missed_position(
                        position, engine, settings, "pin"
                    )
                except AssertionError:
                    continue
                break

        if missed_position is None or result is None:
            self.fail("No missed outcome found for pin fixture positions")

        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "pin")
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
    def test_correspondence_pin_records_failed_attempt_outcome(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="correspondence",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("correspondence")

        positions = pin_fixture_positions()

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "pin_correspondence_failed_attempt.duckdb")
        init_schema(conn)

        failed_position = None
        result = None
        with StockfishEngine(settings) as engine:
            for position in positions:
                try:
                    failed_position, result = find_failed_attempt_position(
                        position, engine, settings, "pin"
                    )
                except AssertionError:
                    continue
                break

        if failed_position is None or result is None:
            self.fail("No failed_attempt outcome found for pin fixture positions")

        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "pin")
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
