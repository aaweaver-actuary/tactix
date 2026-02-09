from __future__ import annotations

import unittest

from tactix.build_position_id__positions import _build_position_id


class PositionIdHashTests(unittest.TestCase):
    def test_position_id_stable_for_same_fen_and_side(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"
        first = _build_position_id(fen, "white")
        second = _build_position_id(fen, "white")
        self.assertEqual(first, second)

    def test_position_id_changes_when_side_to_move_changes(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"
        white_id = _build_position_id(fen, "white")
        black_id = _build_position_id(fen, "black")
        self.assertNotEqual(white_id, black_id)


if __name__ == "__main__":
    unittest.main()
