from pathlib import Path
import unittest
from unittest.mock import patch

import tactix.position_extractor as position_extractor
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


def _read_promotion_en_passant_games() -> list[str]:
    path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "lichess_promotion_en_passant.pgn"
    )
    return [
        chunk.strip() for chunk in path.read_text().split("\n\n\n") if chunk.strip()
    ]


def _read_castling_games() -> list[str]:
    path = (
        Path(__file__).resolve().parent / "fixtures" / "lichess_castling_both_sides.pgn"
    )
    return [
        chunk.strip() for chunk in path.read_text().split("\n\n\n") if chunk.strip()
    ]


def _read_lichess_bullet_games() -> list[str]:
    path = Path(__file__).resolve().parent / "fixtures" / "lichess_bullet_sample.pgn"
    return [
        chunk.strip() for chunk in path.read_text().split("\n\n\n") if chunk.strip()
    ]


def _read_lichess_blitz_games() -> list[str]:
    path = Path(__file__).resolve().parent / "fixtures" / "lichess_blitz_sample.pgn"
    return [
        chunk.strip() for chunk in path.read_text().split("\n\n\n") if chunk.strip()
    ]


def _read_lichess_classical_games() -> list[str]:
    path = Path(__file__).resolve().parent / "fixtures" / "lichess_classical_sample.pgn"
    return [
        chunk.strip() for chunk in path.read_text().split("\n\n\n") if chunk.strip()
    ]


def _read_lichess_correspondence_games() -> list[str]:
    path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "lichess_correspondence_sample.pgn"
    )
    return [
        chunk.strip() for chunk in path.read_text().split("\n\n\n") if chunk.strip()
    ]


class PositionExtractorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.games = _read_fixture_games()
        self.chesscom_games = _read_chesscom_games()
        self.promotion_en_passant_games = _read_promotion_en_passant_games()
        self.castling_games = _read_castling_games()
        self.lichess_bullet_games = _read_lichess_bullet_games()
        self.lichess_blitz_games = _read_lichess_blitz_games()
        self.lichess_classical_games = _read_lichess_classical_games()
        self.lichess_correspondence_games = _read_lichess_correspondence_games()

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

    def test_extracts_lichess_bullet_black_to_move_positions(self) -> None:
        pgn = self.lichess_bullet_games[1]
        positions = extract_positions(
            pgn,
            user="andy_andy_andy",
            source="lichess",
            game_id="bullet1",
            side_to_move_filter="black",
        )
        self.assertGreater(len(positions), 0)
        self.assertTrue(all(pos["side_to_move"] == "black" for pos in positions))

        first = positions[0]
        self.assertEqual(first["ply"], 1)
        self.assertEqual(first["move_number"], 1)
        self.assertEqual(first["side_to_move"], "black")
        self.assertEqual(first["uci"], "d7d5")
        self.assertEqual(first["san"], "d5")
        self.assertEqual(first["clock_seconds"], 60)
        self.assertTrue(first["is_legal"])

    def test_lichess_bullet_black_filter_skips_white_user(self) -> None:
        pgn = self.lichess_bullet_games[0]
        positions = extract_positions(
            pgn,
            user="andy_andy_andy",
            source="lichess",
            game_id="bullet2",
            side_to_move_filter="black",
        )
        self.assertEqual(positions, [])

    def test_extracts_lichess_classical_black_to_move_positions(self) -> None:
        pgn = self.lichess_classical_games[1]
        positions = extract_positions(
            pgn,
            user="lichess",
            source="lichess",
            game_id="classical1",
            side_to_move_filter="black",
        )
        self.assertGreater(len(positions), 0)
        self.assertTrue(all(pos["side_to_move"] == "black" for pos in positions))

        first = positions[0]
        self.assertEqual(first["ply"], 1)
        self.assertEqual(first["move_number"], 1)
        self.assertEqual(first["side_to_move"], "black")
        self.assertEqual(first["uci"], "e7e5")
        self.assertEqual(first["san"], "e5")
        self.assertEqual(first["clock_seconds"], 1800)
        self.assertTrue(first["is_legal"])

        second = positions[1]
        self.assertEqual(second["ply"], 3)
        self.assertEqual(second["move_number"], 2)
        self.assertEqual(second["uci"], "b8c6")
        self.assertEqual(second["clock_seconds"], 1794)
        self.assertTrue(second["is_legal"])

    def test_lichess_classical_black_filter_skips_white_user(self) -> None:
        pgn = self.lichess_classical_games[0]
        positions = extract_positions(
            pgn,
            user="lichess",
            source="lichess",
            game_id="classical2",
            side_to_move_filter="black",
        )
        self.assertEqual(positions, [])

    def test_extracts_lichess_correspondence_black_to_move_positions(self) -> None:
        pgn = self.lichess_correspondence_games[1]
        positions = extract_positions(
            pgn,
            user="lichess",
            source="lichess",
            game_id="corr1",
            side_to_move_filter="black",
        )
        self.assertGreater(len(positions), 0)
        self.assertTrue(all(pos["side_to_move"] == "black" for pos in positions))

        first = positions[0]
        self.assertEqual(first["ply"], 1)
        self.assertEqual(first["move_number"], 1)
        self.assertEqual(first["side_to_move"], "black")
        self.assertEqual(first["uci"], "c7c5")
        self.assertEqual(first["san"], "c5")
        self.assertIsNone(first["clock_seconds"])
        self.assertTrue(first["is_legal"])

    def test_lichess_correspondence_black_filter_skips_white_user(self) -> None:
        pgn = self.lichess_correspondence_games[0]
        positions = extract_positions(
            pgn,
            user="lichess",
            source="lichess",
            game_id="corr2",
            side_to_move_filter="black",
        )
        self.assertEqual(positions, [])

    def test_extracts_lichess_classical_second_black_move_clock(self) -> None:
        pgn = self.lichess_classical_games[1]
        positions = extract_positions(
            pgn,
            user="lichess",
            source="lichess",
            game_id="classical3",
            side_to_move_filter="black",
        )
        self.assertGreaterEqual(len(positions), 2)

        second = positions[1]
        self.assertEqual(second["ply"], 3)
        self.assertEqual(second["move_number"], 2)
        self.assertEqual(second["uci"], "b8c6")
        self.assertEqual(second["clock_seconds"], 1794)
        self.assertTrue(second["is_legal"])

    def test_extracts_lichess_blitz_white_to_move_positions(self) -> None:
        pgn = self.lichess_blitz_games[0]
        positions = extract_positions(
            pgn,
            user="lichess",
            source="lichess",
            game_id="blitz1",
            side_to_move_filter="white",
        )
        self.assertGreater(len(positions), 0)
        self.assertTrue(all(pos["side_to_move"] == "white" for pos in positions))

        first = positions[0]
        self.assertEqual(first["ply"], 0)
        self.assertEqual(first["move_number"], 1)
        self.assertEqual(first["side_to_move"], "white")
        self.assertEqual(first["uci"], "d2d4")
        self.assertEqual(first["san"], "d4")
        self.assertEqual(first["clock_seconds"], 300)
        self.assertTrue(first["is_legal"])

    def test_extracts_lichess_blitz_black_to_move_positions(self) -> None:
        pgn = self.lichess_blitz_games[1]
        positions = extract_positions(
            pgn,
            user="lichess",
            source="lichess",
            game_id="blitz3",
            side_to_move_filter="black",
        )
        self.assertGreater(len(positions), 0)
        self.assertTrue(all(pos["side_to_move"] == "black" for pos in positions))

        first = positions[0]
        self.assertEqual(first["ply"], 1)
        self.assertEqual(first["move_number"], 1)
        self.assertEqual(first["side_to_move"], "black")
        self.assertEqual(first["uci"], "c7c5")
        self.assertEqual(first["san"], "c5")
        self.assertEqual(first["clock_seconds"], 300)
        self.assertTrue(first["is_legal"])

    def test_lichess_blitz_black_filter_skips_white_user(self) -> None:
        pgn = self.lichess_blitz_games[0]
        positions = extract_positions(
            pgn,
            user="lichess",
            source="lichess",
            game_id="blitz4",
            side_to_move_filter="black",
        )
        self.assertEqual(positions, [])

    def test_extracts_lichess_rapid_black_to_move_positions(self) -> None:
        pgn = self.games[1]
        positions = extract_positions(
            pgn,
            user="lichess",
            source="lichess",
            game_id="rapid1",
            side_to_move_filter="black",
        )
        self.assertGreater(len(positions), 0)
        self.assertTrue(all(pos["side_to_move"] == "black" for pos in positions))

        first = positions[0]
        self.assertEqual(first["ply"], 1)
        self.assertEqual(first["move_number"], 1)
        self.assertEqual(first["side_to_move"], "black")
        self.assertEqual(first["uci"], "c7c5")
        self.assertEqual(first["san"], "c5")
        self.assertEqual(first["clock_seconds"], 600)
        self.assertTrue(first["is_legal"])

    def test_lichess_rapid_black_filter_skips_white_user(self) -> None:
        pgn = self.games[0]
        positions = extract_positions(
            pgn,
            user="lichess",
            source="lichess",
            game_id="rapid2",
            side_to_move_filter="black",
        )
        self.assertEqual(positions, [])

    def test_lichess_blitz_white_filter_skips_black_user(self) -> None:
        pgn = self.lichess_blitz_games[1]
        positions = extract_positions(
            pgn,
            user="lichess",
            source="lichess",
            game_id="blitz2",
            side_to_move_filter="white",
        )
        self.assertEqual(positions, [])

    def test_non_user_game_is_skipped(self) -> None:
        pgn = self.games[0]
        positions = extract_positions(
            pgn, user="someoneelse", source="lichess", game_id="fixture1"
        )
        self.assertEqual(positions, [])

    def test_extracts_en_passant_move(self) -> None:
        pgn = self.promotion_en_passant_games[0]
        positions = extract_positions(
            pgn, user="ep_user", source="lichess", game_id="ep1"
        )
        ep_positions = [pos for pos in positions if pos["uci"] == "e5d6"]
        self.assertEqual(len(ep_positions), 1)

        en_passant = ep_positions[0]
        self.assertEqual(en_passant["san"], "exd6")
        self.assertEqual(en_passant["ply"], 4)
        self.assertEqual(en_passant["move_number"], 3)
        self.assertEqual(en_passant["side_to_move"], "white")

    def test_extracts_promotion_move(self) -> None:
        pgn = self.promotion_en_passant_games[1]
        positions = extract_positions(
            pgn, user="promo_user", source="lichess", game_id="promo1"
        )
        promo_positions = [pos for pos in positions if pos["uci"] == "b7a8q"]
        self.assertEqual(len(promo_positions), 1)

        promotion = promo_positions[0]
        self.assertEqual(promotion["san"], "bxa8=Q")
        self.assertEqual(promotion["ply"], 8)
        self.assertEqual(promotion["move_number"], 5)
        self.assertEqual(promotion["side_to_move"], "white")

    def test_extracts_kingside_castle(self) -> None:
        pgn = self.castling_games[0]
        positions = extract_positions(
            pgn, user="castle_white", source="lichess", game_id="castle1"
        )
        castles = [pos for pos in positions if pos["san"] == "O-O"]
        self.assertEqual(len(castles), 1)

        castle = castles[0]
        self.assertEqual(castle["uci"], "e1g1")
        self.assertEqual(castle["ply"], 8)
        self.assertEqual(castle["move_number"], 5)
        self.assertEqual(castle["side_to_move"], "white")

    def test_extracts_queenside_castle(self) -> None:
        pgn = self.castling_games[1]
        positions = extract_positions(
            pgn, user="castle_black", source="lichess", game_id="castle2"
        )
        castles = [pos for pos in positions if pos["san"] == "O-O-O"]
        self.assertEqual(len(castles), 1)

        castle = castles[0]
        self.assertEqual(castle["uci"], "e8c8")
        self.assertEqual(castle["ply"], 9)
        self.assertEqual(castle["move_number"], 5)
        self.assertEqual(castle["side_to_move"], "black")

    def test_clock_from_comment_parses_mm_ss(self) -> None:
        seconds = position_extractor._clock_from_comment("[%clk 05:30]")
        self.assertEqual(seconds, 330.0)

    def test_clock_from_comment_parses_hh_mm_ss(self) -> None:
        seconds = position_extractor._clock_from_comment("[%clk 01:02:03]")
        self.assertEqual(seconds, 3723.0)

    def test_clock_from_comment_invalid_returns_none(self) -> None:
        seconds = position_extractor._clock_from_comment("[%clk bad]")
        self.assertIsNone(seconds)

    def test_extract_positions_uses_python_path_in_pytest(self) -> None:
        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "1"}):
            with patch.object(
                position_extractor,
                "_extract_positions_python",
                return_value=[{"uci": "e2e4"}],
            ) as extractor:
                result = position_extractor.extract_positions(
                    '[Event "Test"]\n\n1. e4 e5 *',
                    user="white",
                    source="lichess",
                    game_id="test",
                )
        self.assertEqual(result, [{"uci": "e2e4"}])
        extractor.assert_called_once()


if __name__ == "__main__":
    unittest.main()
