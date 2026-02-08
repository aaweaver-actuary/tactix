from pathlib import Path
import unittest

from tactix.PgnContext import PgnContext
from tactix.pgn_utils import extract_game_id, split_pgn_chunks


class PgnFixtureParsingTests(unittest.TestCase):
    def test_chesscom_bullet_fixture_parses_expected_values(self) -> None:
        fixture_path = Path(__file__).resolve().parent / "fixtures" / "chesscom_bullet_sample.pgn"
        chunks = split_pgn_chunks(fixture_path.read_text(encoding="utf-8"))
        self.assertGreater(len(chunks), 0)
        pgn = chunks[0]

        ctx = PgnContext(pgn=pgn, user="chesscom", source="chesscom")
        headers = ctx.headers

        self.assertEqual(headers.get("UTCDate"), "2024.07.03")
        self.assertEqual(headers.get("Site"), "https://www.chess.com/game/live/2234567890")
        self.assertEqual(headers.get("TimeControl"), "60")
        self.assertEqual(headers.get("Result"), "1-0")

        game = ctx.game
        self.assertIsNotNone(game)
        board = game.board()
        moves = list(game.mainline_moves())
        for move in moves:
            board.push(move)

        self.assertEqual(len(moves), 10)
        self.assertEqual(
            board.fen(),
            "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6",
        )

        game_id_first = extract_game_id(pgn)
        game_id_second = extract_game_id(pgn)
        self.assertEqual(game_id_first, "2234567890")
        self.assertEqual(game_id_first, game_id_second)
