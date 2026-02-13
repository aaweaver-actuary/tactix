import shutil
import unittest

import chess

from tactix._evaluate_engine_position import _evaluate_engine_position
from tactix.StockfishEngine import StockfishEngine
from tactix.analyze_position import analyze_position
from tactix.db.tactic_repository_provider import upsert_tactic_with_outcome
from tests.conversion_test_helpers import (
    build_settings__chesscom_blitz_stockfish,
    create_connection__conversion,
    fetch_conversion__by_tactic_id,
    insert_position__single,
)


class ConversionPlayedMateLineTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_mate_line_first_move_marks_conversion(self) -> None:
        settings = build_settings__chesscom_blitz_stockfish()

        fen = "7k/5Q2/7K/8/8/8/8/8 w - - 0 1"
        board = chess.Board(fen)

        conn = create_connection__conversion("conversion_played_mate_line.duckdb")

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

            insert_position__single(conn, position)

            result = analyze_position(position, engine, settings=settings)

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertIsNotNone(tactic_row.get("best_line_uci"))
        self.assertEqual(str(tactic_row["best_line_uci"]).split()[0], user_move.uci())

        tactic_id = upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
        conversion = fetch_conversion__by_tactic_id(conn, tactic_id)

        self.assertIsNotNone(conversion)
        self.assertTrue(conversion[0])
        self.assertEqual(conversion[1], "played_mate_line")
        self.assertEqual(conversion[2], "found")
        self.assertEqual(conversion[3], user_move.uci())


if __name__ == "__main__":
    unittest.main()
