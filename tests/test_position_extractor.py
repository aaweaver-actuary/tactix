from pathlib import Path
import unittest

from tactix.position_extractor import extract_positions


def _read_fixture_games() -> list[str]:
    path = Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
    return [
        chunk.strip() for chunk in path.read_text().split("\n\n\n") if chunk.strip()
    ]


def _read_chesscom_games() -> list[str]:
    path = Path(__file__).resolve().parent / "fixtures" / "chesscom_blitz_sample.pgn"
    return [
        chunk.strip() for chunk in path.read_text().split("\n\n\n") if chunk.strip()
    ]


class PositionExtractorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.games = _read_fixture_games()
        self.chesscom_games = _read_chesscom_games()

    def test_extracts_only_user_to_move_positions(self) -> None:
        pgn = self.games[0]
        positions = extract_positions(
            pgn, user="lichess", source="lichess", game_id="fixture1"
        )
        self.assertGreater(len(positions), 0)

        first = positions[0]
        self.assertEqual(first["ply"], 0)
        self.assertEqual(first["move_number"], 1)
        self.assertEqual(first["side_to_move"], "white")
        self.assertEqual(first["uci"], "d2d4")
        self.assertEqual(first["san"], "d4")
        self.assertEqual(first["clock_seconds"], 600)
        self.assertTrue(first["fen"].startswith("rnbqkbnr/pppppppp/8/8/"))

    def test_extracts_chesscom_white_positions_with_clocks(self) -> None:
        pgn = self.chesscom_games[0]
        positions = extract_positions(
            pgn, user="chesscom", source="chesscom", game_id="chesscom1"
        )
        self.assertGreater(len(positions), 0)

        first = positions[0]
        self.assertEqual(first["ply"], 0)
        self.assertEqual(first["move_number"], 1)
        self.assertEqual(first["side_to_move"], "white")
        self.assertEqual(first["uci"], "e2e4")
        self.assertEqual(first["san"], "e4")
        self.assertEqual(first["clock_seconds"], 300)

    def test_extracts_chesscom_black_positions_with_clocks(self) -> None:
        pgn = self.chesscom_games[1]
        positions = extract_positions(
            pgn, user="chesscom", source="chesscom", game_id="chesscom2"
        )
        self.assertGreater(len(positions), 0)

        first = positions[0]
        self.assertEqual(first["ply"], 1)
        self.assertEqual(first["move_number"], 1)
        self.assertEqual(first["side_to_move"], "black")
        self.assertEqual(first["uci"], "d7d5")
        self.assertEqual(first["san"], "d5")
        self.assertEqual(first["clock_seconds"], 300)

    def test_non_user_game_is_skipped(self) -> None:
        pgn = self.games[0]
        positions = extract_positions(
            pgn, user="someoneelse", source="lichess", game_id="fixture1"
        )
        self.assertEqual(positions, [])


if __name__ == "__main__":
    unittest.main()
