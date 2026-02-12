import shutil
import tempfile
import unittest
from pathlib import Path

from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from tactix.config import Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tactix.extract_positions import extract_positions
from tactix.pgn_utils import split_pgn_chunks
from tactix.tactic_scope import is_supported_motif


@unittest.skipUnless(
    is_supported_motif("mate", mate_in=2),
    "Mate in 2 disabled in current scope",
)
class MateInTwoOpportunityTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_mate_in_two_creates_opportunity_with_best_line(self) -> None:
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

        fixture_path = Path(__file__).resolve().parent / "fixtures" / "chesscom_bullet_sample.pgn"
        chunks = split_pgn_chunks(fixture_path.read_text())
        mate_pgn = next(chunk for chunk in chunks if "Bullet Fixture 4" in chunk)

        positions = extract_positions(
            mate_pgn,
            settings.chesscom_user,
            settings.source,
            game_id="mate-in-two-opportunity",
            side_to_move_filter="black",
        )
        position = next(pos for pos in positions if pos["uci"] == "c5f2")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "mate_in_two_opportunity.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertEqual(tactic_row["mate_in"], 2)
        self.assertGreaterEqual(tactic_row["severity"], 1.5)
        self.assertIsNone(tactic_row["target_piece"])
        self.assertIsNone(tactic_row["target_square"])

        best_line_uci = tactic_row.get("best_line_uci")
        self.assertIsNotNone(best_line_uci)
        self.assertIn("c5f2", str(best_line_uci).split())

        engine_depth = tactic_row.get("engine_depth")
        self.assertIsNotNone(engine_depth)
        self.assertGreaterEqual(int(engine_depth), 1)

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored = conn.execute(
            """
            SELECT position_id, best_line_uci, engine_depth, created_at
            FROM tactics
            WHERE tactic_id = ?
            """,
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored[0], position_ids[0])
        self.assertIn("c5f2", str(stored[1] or "").split())
        self.assertIsNotNone(stored[2])
        self.assertIsNotNone(stored[3])

        upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        count = conn.execute(
            "SELECT COUNT(*) FROM tactics WHERE position_id = ?",
            [position_ids[0]],
        ).fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
