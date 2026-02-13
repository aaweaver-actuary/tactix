import shutil
import tempfile
import unittest
from pathlib import Path

import chess

from tactix._evaluate_engine_position import _evaluate_engine_position
from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from tactix.config import Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome


class ConversionPlayedMateLineTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_mate_line_first_move_marks_conversion(self) -> None:
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

        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "conversion_played_mate_line.duckdb")
        init_schema(conn)

        with StockfishEngine(settings) as engine:
            (
                _best_move_obj,
                _best_move,
                _base_cp,
                mate_in_one,
                mate_in_two,
                best_line_uci,
                _engine_depth,
            ) = _evaluate_engine_position(board, engine, board.turn, board)
            self.assertTrue(mate_in_one or mate_in_two)
            self.assertIsNotNone(best_line_uci)

            first_move_uci = str(best_line_uci).split()[0]
            user_move = chess.Move.from_uci(first_move_uci)
            self.assertIn(user_move, board.legal_moves)

            position = {
                "game_id": "conversion-played-mate-line",
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

            position_ids = insert_positions(conn, [position])
            position["position_id"] = position_ids[0]

            result = analyze_position(position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertIsNotNone(tactic_row.get("best_line_uci"))
        self.assertEqual(str(tactic_row["best_line_uci"]).split()[0], user_move.uci())

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        conversion = conn.execute(
            """
            SELECT converted, conversion_reason, result, user_uci
            FROM conversions
            WHERE opportunity_id = ?
            """,
            [tactic_id],
        ).fetchone()

        self.assertIsNotNone(conversion)
        self.assertTrue(conversion[0])
        self.assertEqual(conversion[1], "played_mate_line")
        self.assertEqual(conversion[2], "found")
        self.assertEqual(conversion[3], user_move.uci())


if __name__ == "__main__":
    unittest.main()
