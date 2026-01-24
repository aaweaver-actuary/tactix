from pathlib import Path
import unittest

from tactix.position_extractor import extract_positions


def _read_fixture_games() -> list[str]:
    path = Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
    return [
        chunk.strip() for chunk in path.read_text().split("\n\n\n") if chunk.strip()
    ]


class PositionExtractorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.games = _read_fixture_games()

    def test_extracts_only_user_to_move_positions(self) -> None:
        pgn = self.games[0]
        positions = extract_positions(
            pgn, user="lichess", source="lichess", game_id="fixture1"
        )
        self.assertGreater(len(positions), 0)

        first = positions[0]
        self.assertEqual(first["ply"], 0)
        self.assertEqual(first["move_number"], 1)
        self.assertEqual(first["uci"], "d2d4")
        self.assertEqual(first["san"], "d4")
        self.assertEqual(first["clock_seconds"], 600)
        self.assertTrue(first["fen"].startswith("rnbqkbnr/pppppppp/8/8/"))

    def test_non_user_game_is_skipped(self) -> None:
        pgn = self.games[0]
        positions = extract_positions(
            pgn, user="someoneelse", source="lichess", game_id="fixture1"
        )
        self.assertEqual(positions, [])


if __name__ == "__main__":
    unittest.main()
