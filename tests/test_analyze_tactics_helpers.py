import unittest
from unittest.mock import patch

import chess

from tactix.config import Settings
from tactix.engine_result import EngineResult
from tactix import analyze_tactics__positions as impl


class DummyEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def __enter__(self) -> "DummyEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def analyse(self, board: chess.Board) -> EngineResult:
        return EngineResult(best_move=None, score_cp=0, depth=0)


class AnalyzeTacticsHelperTests(unittest.TestCase):
    def test_is_profile_in_handles_chesscom_daily(self) -> None:
        settings = Settings(source="chesscom")
        settings.chesscom_profile = "daily"
        self.assertTrue(impl._is_profile_in(settings, {"correspondence"}))

    def test_is_profile_in_handles_empty_profile(self) -> None:
        settings = Settings(source="chesscom")
        settings.chesscom_profile = ""
        settings.chesscom.time_class = ""
        self.assertFalse(impl._is_profile_in(settings, {"rapid"}))

    def test_parse_user_move_invalid_uci(self) -> None:
        board = chess.Board()
        move = impl._parse_user_move(board, "invalid", board.fen())
        self.assertIsNone(move)

    def test_parse_user_move_illegal_move(self) -> None:
        board = chess.Board()
        move = impl._parse_user_move(board, "e2e5", board.fen())
        self.assertIsNone(move)

    def test_score_best_line_returns_none_without_best_move(self) -> None:
        board = chess.Board()
        result = impl._score_best_line__after_move(board, None, DummyEngine(Settings()), True)
        self.assertIsNone(result)

    def test_compare_move_best_line_returns_none_when_best_move_none(self) -> None:
        board = chess.Board()
        result = impl._compare_move__best_line(board, None, "e2e4", 0, DummyEngine(Settings()), True)
        self.assertIsNone(result)

    def test_compute_eval_swing_thresholds(self) -> None:
        self.assertEqual(impl._compute_eval__swing_threshold("pin", None), -50)
        self.assertEqual(impl._compute_eval__swing_threshold("skewer", None), -50)
        self.assertEqual(impl._compute_eval__swing_threshold("discovered_attack", None), -50)
        self.assertIsNone(impl._compute_eval__swing_threshold("fork", None))

    def test_apply_outcome_failed_attempt_line_tactics_overrides(self) -> None:
        result, motif = impl._apply_outcome__failed_attempt_line_tactics(
            "unclear",
            "pin",
            None,
            -100,
            None,
        )
        self.assertEqual(result, "failed_attempt")
        self.assertEqual(motif, "pin")

        result, motif = impl._apply_outcome__failed_attempt_line_tactics(
            "unclear",
            "skewer",
            None,
            -100,
            None,
        )
        self.assertEqual(result, "failed_attempt")
        self.assertEqual(motif, "skewer")

        result, motif = impl._apply_outcome__failed_attempt_line_tactics(
            "unclear",
            "discovered_attack",
            None,
            -100,
            None,
        )
        self.assertEqual(result, "failed_attempt")
        self.assertEqual(motif, "discovered_attack")

    def test_analyze_positions_collects_rows_and_skips_invalid(self) -> None:
        board = chess.Board()
        positions = [
            {"game_id": "valid-1", "fen": board.fen(), "uci": "e2e4"},
            {"game_id": "invalid-1", "fen": board.fen(), "uci": "e2e5"},
        ]
        with patch.object(impl, "StockfishEngine", DummyEngine):
            tactics_rows, outcomes_rows = impl.analyze_positions(positions, Settings())
        self.assertEqual(len(tactics_rows), 1)
        self.assertEqual(len(outcomes_rows), 1)


if __name__ == "__main__":
    unittest.main()
