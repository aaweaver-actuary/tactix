import unittest

import chess
import chess.engine

from tactix import engine_result as impl


class EngineResultHelperTests(unittest.TestCase):
    def test_select_engine_info_prefers_multipv(self) -> None:
        info = impl._select_engine_info([
            {"multipv": 2, "depth": 1},
            {"multipv": 1, "depth": 3},
        ])
        self.assertEqual(info.get("multipv"), 1)

    def test_select_engine_info_empty_list(self) -> None:
        info = impl._select_engine_info([])
        self.assertEqual(info, {})

    def test_resolve_pov_score_handles_none(self) -> None:
        self.assertIsNone(impl._resolve_pov_score(None, None))

    def test_resolve_pov_score_pov_score(self) -> None:
        board = chess.Board()
        score = chess.engine.PovScore(chess.engine.Cp(50), chess.WHITE)
        resolved = impl._resolve_pov_score(score, board)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.score(mate_score=100000), 50)

    def test_resolve_pov_score_black_turn(self) -> None:
        board = chess.Board()
        board.turn = chess.BLACK
        score = chess.engine.Cp(90)
        resolved = impl._resolve_pov_score(score, board)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.score(mate_score=100000), -90)

    def test_score_value_and_mate(self) -> None:
        value, mate_in = impl._score_value_and_mate(chess.engine.Cp(120))
        self.assertEqual(value, 120)
        self.assertIsNone(mate_in)

    def test_best_move_and_depth_from_info(self) -> None:
        move = chess.Move.from_uci("e2e4")
        info = {"pv": [move], "depth": 4}
        self.assertEqual(impl._best_move_from_info(info), move)
        self.assertEqual(impl._depth_from_info(info), 4)


if __name__ == "__main__":
    unittest.main()
