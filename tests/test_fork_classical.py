import shutil
import tempfile
import unittest
from pathlib import Path

from tactix.config import DEFAULT_CLASSICAL_STOCKFISH_DEPTH, Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tactix.db.tactic_repository_provider import tactic_repository
from tactix.pgn_utils import split_pgn_chunks
from tactix.extract_positions import extract_positions
from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from tactix.tactic_scope import is_supported_motif


@unittest.skipUnless(is_supported_motif("fork"), "Fork disabled in current scope")
class TestForkClassical(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_classical_fork_is_high_severity(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_classical_fork_sample.pgn"
        )
        chunks = split_pgn_chunks(fixture_path.read_text())
        fork_pgn = chunks[0]

        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_profile="classical",
            fork_severity_floor=1.5,
            stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
            stockfish_movetime_ms=60,
            stockfish_depth=None,
            stockfish_multipv=1,
        )
        settings.apply_chesscom_profile("classical")
        self.assertEqual(settings.stockfish_depth, DEFAULT_CLASSICAL_STOCKFISH_DEPTH)

        positions = extract_positions(
            fork_pgn,
            settings.chesscom_user,
            settings.source,
            game_id="classical-fork",
            side_to_move_filter="black",
        )
        fork_position = next(pos for pos in positions if pos["uci"] == "f4e2")

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "fork_classical.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [fork_position])
        fork_position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(fork_position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "fork")
        self.assertEqual(tactic_row["best_uci"], "f4e2")
        self.assertGreaterEqual(tactic_row["severity"], 1.5)

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored = conn.execute(
            "SELECT position_id, best_san, explanation FROM tactics WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored[0], position_ids[0])
        self.assertIsNotNone(stored[1])
        self.assertIn("Best line", stored[2] or "")

        attempt = tactic_repository(conn).grade_practice_attempt(
            tactic_id,
            position_ids[0],
            "f4e2",
        )
        self.assertIn("Best line", attempt["explanation"] or "")
        self.assertIn("e2", attempt["explanation"] or "")


if __name__ == "__main__":
    unittest.main()
