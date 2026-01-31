import unittest

import chess

from tactix.config import Settings
from tactix.stockfish_runner import EngineResult
from tactix.tactic_detectors import (
    BaseTacticDetector,
    build_default_motif_detector_suite,
)
from tactix.tactics_analyzer import _is_profile_in, analyze_position


class TacticsAnalyzerTests(unittest.TestCase):
    def test_classify_result_variants(self) -> None:
        self.assertEqual(
            BaseTacticDetector.classify_result("e2e4", "e2e4", 0, 120),
            ("found", 120),
        )
        self.assertEqual(
            BaseTacticDetector.classify_result("e2e4", "d2d4", 100, -250),
            ("missed", -350),
        )
        self.assertEqual(
            BaseTacticDetector.classify_result(None, "d2d4", -50, -200),
            ("failed_attempt", -150),
        )
        self.assertEqual(
            BaseTacticDetector.classify_result("e2e4", "d2d4", 20, -30),
            ("unclear", -50),
        )

    def test_score_from_pov(self) -> None:
        self.assertEqual(BaseTacticDetector.score_from_pov(120, chess.WHITE, chess.WHITE), 120)
        self.assertEqual(BaseTacticDetector.score_from_pov(120, chess.WHITE, chess.BLACK), -120)
        self.assertEqual(BaseTacticDetector.score_from_pov(-80, chess.BLACK, chess.WHITE), 80)

    def test_infer_motif_fork_detection(self) -> None:
        suite = build_default_motif_detector_suite()
        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.F5, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.QUEEN, chess.BLACK))
        board.set_piece_at(chess.F7, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.turn = chess.WHITE

        motif = suite.infer_motif(board, chess.Move.from_uci("f5d6"))
        self.assertEqual(motif, "fork")

    def test_infer_motif_hanging_capture(self) -> None:
        suite = build_default_motif_detector_suite()
        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.C4, chess.Piece(chess.BISHOP, chess.WHITE))
        board.set_piece_at(chess.E6, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.turn = chess.WHITE

        motif = suite.infer_motif(board, chess.Move.from_uci("c4e6"))
        self.assertEqual(motif, "hanging_piece")

    def test_is_profile_in_handles_chesscom_daily(self) -> None:
        chesscom_daily = Settings(source="chesscom", chesscom_profile="daily")
        self.assertTrue(_is_profile_in(chesscom_daily, {"correspondence"}))
        self.assertFalse(_is_profile_in(chesscom_daily, {"bullet", "blitz"}))

    def test_is_profile_in_normalizes_profiles(self) -> None:
        lichess_rapid = Settings(source="lichess", lichess_profile="Rapid")
        self.assertTrue(_is_profile_in(lichess_rapid, {"rapid"}))
        self.assertFalse(_is_profile_in(lichess_rapid, {"blitz"}))

    def test_mate_in_two_unclear_reclassified_failed_attempt(self) -> None:
        class StubEngine:
            def __init__(self) -> None:
                self.calls = 0

            def analyse(self, board: chess.Board) -> EngineResult:
                self.calls += 1
                score_cp = 100000 if board.turn == chess.WHITE else -100000
                return EngineResult(
                    best_move=chess.Move.from_uci("e2e4"),
                    score_cp=score_cp,
                    depth=12,
                    mate_in=2,
                )

        position = {
            "game_id": "unit-mate-in-two",
            "fen": chess.STARTING_FEN,
            "uci": "d2d4",
        }

        result = analyze_position(position, StubEngine())

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "mate")
        self.assertEqual(outcome_row["result"], "failed_attempt")

    def test_fork_missed_reclassified_failed_attempt(self) -> None:
        class StubEngine:
            def __init__(self) -> None:
                self.calls = 0

            def analyse(self, board: chess.Board) -> EngineResult:
                self.calls += 1
                return EngineResult(
                    best_move=chess.Move.from_uci("f5e7"),
                    score_cp=200,
                    depth=12,
                    mate_in=None,
                )

        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.F5, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.QUEEN, chess.BLACK))
        board.set_piece_at(chess.F7, chess.Piece(chess.ROOK, chess.BLACK))
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.turn = chess.WHITE

        position = {
            "game_id": "unit-fork-failed-attempt",
            "fen": board.fen(),
            "uci": "f5d6",
        }

        result = analyze_position(position, StubEngine())

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "fork")
        self.assertEqual(outcome_row["result"], "failed_attempt")

    def test_discovered_attack_unclear_reclassified_failed_attempt(self) -> None:
        class StubEngine:
            def __init__(self) -> None:
                self.calls = 0

            def analyse(self, board: chess.Board) -> EngineResult:
                self.calls += 1
                if self.calls == 1:
                    return EngineResult(
                        best_move=chess.Move.from_uci("a2c1"),
                        score_cp=0,
                        depth=12,
                        mate_in=None,
                    )
                if self.calls == 2:
                    return EngineResult(
                        best_move=None,
                        score_cp=50,
                        depth=12,
                        mate_in=None,
                    )
                return EngineResult(
                    best_move=None,
                    score_cp=-10,
                    depth=12,
                    mate_in=None,
                )

        board = chess.Board(None)
        board.clear()
        board.set_piece_at(chess.H1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
        board.set_piece_at(chess.A2, chess.Piece(chess.KNIGHT, chess.WHITE))
        board.set_piece_at(chess.G2, chess.Piece(chess.PAWN, chess.WHITE))
        board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
        board.set_piece_at(chess.A8, chess.Piece(chess.QUEEN, chess.BLACK))
        board.turn = chess.WHITE

        position = {
            "game_id": "unit-discovered-attack-failed-attempt",
            "fen": board.fen(),
            "uci": "a2b4",
        }

        result = analyze_position(position, StubEngine())

        self.assertIsNotNone(result)
        tactic_row, outcome_row = result
        self.assertEqual(tactic_row["motif"], "discovered_attack")
        self.assertEqual(outcome_row["result"], "failed_attempt")


if __name__ == "__main__":
    unittest.main()
