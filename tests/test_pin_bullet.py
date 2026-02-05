import shutil
import tempfile
import unittest
from pathlib import Path

from tactix.config import DEFAULT_BULLET_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from tests.fixture_helpers import pin_fixture_position


class PinBulletTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_bullet_pin_is_high_severity(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="bullet",
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("bullet")
        self.assertEqual(settings.stockfish_depth, DEFAULT_BULLET_STOCKFISH_DEPTH)

        position = pin_fixture_position()

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "pin_bullet.duckdb")
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
