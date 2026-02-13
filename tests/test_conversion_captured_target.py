import shutil
import unittest

import chess

from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tests.conversion_test_helpers import (
    build_settings__chesscom_blitz_stockfish,
    create_connection__conversion,
    fetch_conversion__by_tactic_id,
    insert_position__single,
)


class ConversionCapturedTargetTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_hanging_piece_capture_marks_conversion(self) -> None:
        settings = build_settings__chesscom_blitz_stockfish()

        fen = "4k3/8/8/8/3q4/5N2/8/4K3 w - - 0 1"
        board = chess.Board(fen)
        user_move = chess.Move.from_uci("f3d4")
        self.assertTrue(board.is_capture(user_move))
        self.assertIn(user_move, board.legal_moves)

        position = {
            "game_id": "conversion-captured-target",
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

        conn = create_connection__conversion("conversion_captured_target.duckdb")
        insert_position__single(conn, position)

        with StockfishEngine(settings) as engine:
            result = analyze_position(position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "hanging_piece")

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        conversion = fetch_conversion__by_tactic_id(conn, tactic_id)

        self.assertIsNotNone(conversion)
        self.assertTrue(conversion[0])
        self.assertEqual(conversion[1], "captured_target")
        self.assertEqual(conversion[2], "found")
        self.assertEqual(conversion[3], user_move.uci())


if __name__ == "__main__":
    unittest.main()
