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


class MateInOneOpportunityTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_mate_in_one_creates_opportunity_with_best_line(self) -> None:
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

        fen = "7k/5Q2/7K/8/8/8/8/8 w - - 0 1"
        board = chess.Board(fen)
        mate_move = chess.Move.from_uci("f7g7")
        self.assertIn(mate_move, board.legal_moves)
        mate_board = board.copy()
        mate_board.push(mate_move)
        self.assertTrue(mate_board.is_checkmate())

        position = {
            "game_id": "mate-in-one-opportunity",
            "user": "chesscom",
            "source": "chesscom",
            "fen": fen,
            "ply": board.ply(),
            "move_number": board.fullmove_number,
            "side_to_move": "white",
            "uci": mate_move.uci(),
            "san": board.san(mate_move),
            "clock_seconds": None,
            "is_legal": True,
        }

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "mate_in_one_opportunity.duckdb")
        init_schema(conn)
        position_ids = insert_positions(conn, [position])
        position["position_id"] = position_ids[0]

        with StockfishEngine(settings) as engine:
            result = analyze_position(position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertEqual(tactic_row["mate_in"], 1)
        self.assertGreaterEqual(tactic_row["severity"], 1.5)
        self.assertIsNone(tactic_row["target_piece"])
        self.assertIsNone(tactic_row["target_square"])

        best_line_uci = tactic_row.get("best_line_uci")
        self.assertIsNotNone(best_line_uci)
        self.assertIn(mate_move.uci(), str(best_line_uci).split())

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
        self.assertIn(mate_move.uci(), str(stored[1] or "").split())
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
