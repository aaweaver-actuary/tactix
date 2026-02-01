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
        result = impl._compare_move__best_line(
            board, None, "e2e4", 0, DummyEngine(Settings()), True
        )
        self.assertIsNone(result)

    def test_compute_eval_swing_thresholds(self) -> None:
        self.assertEqual(impl._compute_eval__swing_threshold("pin", None), -50)
        self.assertEqual(impl._compute_eval__swing_threshold("skewer", None), -50)
        self.assertEqual(impl._compute_eval__swing_threshold("discovered_attack", None), -50)
        self.assertEqual(impl._compute_eval__swing_threshold("discovered_check", None), -50)
        self.assertEqual(impl._compute_eval__swing_threshold("hanging_piece", None), -50)
        self.assertIsNone(impl._compute_eval__swing_threshold("fork", None))

    def test_compute_eval_fork_unclear_threshold(self) -> None:
        self.assertEqual(impl._compute_eval__fork_unclear_threshold(None), -300)

    def test_compute_eval_skewer_unclear_threshold(self) -> None:
        self.assertEqual(impl._compute_eval__skewer_unclear_threshold(None), -300)

    def test_compute_eval_pin_unclear_threshold(self) -> None:
        self.assertEqual(impl._compute_eval__pin_unclear_threshold(None), -300)

    def test_compute_eval_discovered_attack_unclear_threshold(self) -> None:
        self.assertEqual(impl._compute_eval__discovered_attack_unclear_threshold(None), -300)

    def test_compute_eval_discovered_check_unclear_threshold(self) -> None:
        self.assertEqual(impl._compute_eval__discovered_check_unclear_threshold(None), -300)

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

        result, motif = impl._apply_outcome__failed_attempt_line_tactics(
            "unclear",
            "discovered_check",
            None,
            -100,
            None,
        )
        self.assertEqual(result, "failed_attempt")
        self.assertEqual(motif, "discovered_check")

    def test_apply_outcome_failed_attempt_hanging_piece_override(self) -> None:
        result, motif = impl._apply_outcome__failed_attempt_hanging_piece(
            "unclear",
            "hanging_piece",
            None,
            -100,
            impl._compute_eval__swing_threshold("hanging_piece", None),
        )
        self.assertEqual(result, "failed_attempt")
        self.assertEqual(motif, "hanging_piece")

    def test_apply_outcome_unclear_fork_override(self) -> None:
        result = impl._apply_outcome__unclear_fork(
            "failed_attempt",
            "fork",
            "f5e7",
            "f5d6",
            -20,
            impl._compute_eval__fork_unclear_threshold(None),
        )
        self.assertEqual(result, "unclear")

    def test_apply_outcome_unclear_skewer_override(self) -> None:
        result = impl._apply_outcome__unclear_skewer(
            "failed_attempt",
            "skewer",
            "e2e4",
            "e2e3",
            -20,
            impl._compute_eval__skewer_unclear_threshold(None),
        )
        self.assertEqual(result, "unclear")

    def test_apply_outcome_unclear_pin_override(self) -> None:
        result = impl._apply_outcome__unclear_pin(
            "missed",
            "pin",
            "e2e4",
            "e2e3",
            -20,
            impl._compute_eval__pin_unclear_threshold(None),
        )
        self.assertEqual(result, "unclear")

    def test_apply_outcome_unclear_discovered_attack_override(self) -> None:
        result = impl._apply_outcome__unclear_discovered_attack(
            "missed",
            "discovered_attack",
            "a2a4",
            "a2a3",
            -20,
            impl._compute_eval__discovered_attack_unclear_threshold(None),
        )
        self.assertEqual(result, "unclear")

    def test_apply_outcome_unclear_discovered_check_override(self) -> None:
        result = impl._apply_outcome__unclear_discovered_check(
            "missed",
            "discovered_check",
            "a2a4",
            "a2a3",
            -20,
            impl._compute_eval__discovered_check_unclear_threshold(None),
        )
        self.assertEqual(result, "unclear")

    def test_apply_outcome_unclear_mate_in_one_override(self) -> None:
        result = impl._apply_outcome__unclear_mate_in_one(
            "failed_attempt",
            "d8h4",
            "a2a3",
            300,
            impl.MATE_IN_ONE,
        )
        self.assertEqual(result, "unclear")

        result = impl._apply_outcome__unclear_mate_in_one(
            "missed",
            "d8h4",
            "d8h4",
            300,
            impl.MATE_IN_ONE,
        )
        self.assertEqual(result, "missed")

        result = impl._apply_outcome__unclear_mate_in_one(
            "missed",
            "d8h4",
            "a2a3",
            100,
            impl.MATE_IN_ONE,
        )
        self.assertEqual(result, "missed")

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
