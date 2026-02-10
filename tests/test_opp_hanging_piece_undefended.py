import shutil
import tempfile
import unittest
from pathlib import Path

import chess

from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from tactix.config import Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome


class OppHangingPieceUndefendedTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_opp_hanging_piece_undefended_creates_opportunity(self) -> None:
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

        fen = "4k3/8/8/8/3q4/5N2/8/4K3 w - - 0 1"
        board = chess.Board(fen)
        user_move = chess.Move.from_uci("e1e2")
        position = {
            "game_id": "opp-hanging-undefended",
            "user": "chesscom",
            "source": "chesscom",
            "fen": fen,
            "ply": board.ply(),
            "move_number": board.fullmove_number,
            "side_to_move": "white",
            "uci": user_move.uci(),
            "san": board.san(user_move),
            "clock_seconds": None,
            "is_legal": True,
        }

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "opp_hanging_piece_undefended.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "hanging_piece")
        self.assertEqual(tactic_row["target_piece"], "queen")
        self.assertEqual(tactic_row["target_square"], "d4")
        self.assertGreaterEqual(tactic_row["severity"], 1.5)
        self.assertIn("best_uci", tactic_row)

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        stored = conn.execute(
            "SELECT position_id, target_piece, target_square, created_at FROM tactics WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        self.assertEqual(stored[0], position_ids[0])
        self.assertEqual(stored[1], "queen")
        self.assertEqual(stored[2], "d4")
        self.assertIsNotNone(stored[3])

        upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        count = conn.execute(
            "SELECT COUNT(*) FROM tactics WHERE position_id = ?",
            [position_ids[0]],
        ).fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
