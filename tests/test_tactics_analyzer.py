import unittest
import chess

from tactix.tactics_analyzer import _classify_result, _infer_motif


class TacticsAnalyzerTests(unittest.TestCase):
    def test_classify_result_variants(self) -> None:
        self.assertEqual(_classify_result("e2e4", "e2e4", 0, 120), ("found", 120))
        self.assertEqual(_classify_result("e2e4", "d2d4", 100, -250), ("missed", -350))
        self.assertEqual(
            _classify_result(None, "d2d4", -50, -200), ("failed_attempt", -150)
        )

    def test_infer_motif_fork_detection(self) -> None:
        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.F5, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.QUEEN, chess.BLACK))
        board.set_piece_at(chess.F7, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.turn = chess.WHITE

        motif = _infer_motif(board, chess.Move.from_uci("f5d6"))
        self.assertEqual(motif, "fork")

    def test_infer_motif_hanging_capture(self) -> None:
        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.C4, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.E6, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.turn = chess.WHITE

        motif = _infer_motif(board, chess.Move.from_uci("c4e6"))
        self.assertEqual(motif, "hanging_piece")


if __name__ == "__main__":
    unittest.main()
