import unittest
from datetime import datetime, timezone

from tactix.pgn_utils import (
    extract_game_id,
    extract_last_timestamp_ms,
    extract_pgn_metadata,
    latest_timestamp,
)
from unittest.mock import patch


class PgnUtilsHelperTests(unittest.TestCase):
    def test_extract_game_id_uses_site_patterns(self) -> None:
        lichess_pgn = """[Event \"Test\"]
[Site \"https://lichess.org/AbcDef12\"]
[UTCDate \"2020.01.02\"]
[UTCTime \"03:04:05\"]
[White \"user\"]
[Black \"opp\"]
[Result \"*\"]

1. e4 *
"""
        chesscom_pgn = """[Event \"Test\"]
[Site \"https://chess.com/game/live/123456\"]
[UTCDate \"2020.01.02\"]
[UTCTime \"03:04:05\"]
[White \"user\"]
[Black \"opp\"]
[Result \"*\"]

1. d4 *
"""

        self.assertEqual(extract_game_id(lichess_pgn), "AbcDef12")
        self.assertEqual(extract_game_id(chesscom_pgn), "123456")

        unknown_site = (
            '[Event "Test"]\n'
            '[Site "Weird Site 2024/07/game#999999"]\n'
            '[UTCDate "2020.01.02"]\n'
            '[UTCTime "03:04:05"]\n'
            '[White "user"]\n'
            '[Black "opp"]\n'
            '[Result "*"]\n\n'
            '1. e4 *\n'
        )
        self.assertEqual(extract_game_id(unknown_site), "202407game999999")

    def test_extract_last_timestamp_ms_parses_formats(self) -> None:
        dotted = """[Event \"Test\"]
[Site \"https://lichess.org/AbcDef12\"]
[UTCDate \"2020.01.02\"]
[UTCTime \"03:04:05\"]
[White \"user\"]
[Black \"opp\"]
[Result \"*\"]

1. e4 *
"""
        dashed = """[Event \"Test\"]
[Site \"https://lichess.org/AbcDef12\"]
[UTCDate \"2020-01-03\"]
[UTCTime \"10:20:30\"]
[White \"user\"]
[Black \"opp\"]
[Result \"*\"]

1. e4 *
"""

        expected_dotted = int(
            datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc).timestamp() * 1000
        )
        expected_dashed = int(
            datetime(2020, 1, 3, 10, 20, 30, tzinfo=timezone.utc).timestamp() * 1000
        )

        self.assertEqual(extract_last_timestamp_ms(dotted), expected_dotted)
        self.assertEqual(extract_last_timestamp_ms(dashed), expected_dashed)

        with patch("tactix.pgn_utils.time.time", return_value=1000):
            self.assertEqual(extract_last_timestamp_ms("invalid"), 1000 * 1000)

    def test_extract_pgn_metadata_picks_user_rating_and_time_control(self) -> None:
        pgn = """[Event \"Test\"]
[Site \"https://lichess.org/AbcDef12\"]
[UTCDate \"2020.01.02\"]
[UTCTime \"03:04:05\"]
[White \"alice\"]
[Black \"bob\"]
[WhiteElo \"1420\"]
[BlackElo \"1510\"]
[TimeControl \"300+0\"]
[Result \"*\"]

1. e4 *
"""

        metadata_white = extract_pgn_metadata(pgn, user="alice")
        metadata_black = extract_pgn_metadata(pgn, user="bob")

        self.assertEqual(metadata_white["user_rating"], 1420)
        self.assertEqual(metadata_black["user_rating"], 1510)
        self.assertEqual(metadata_white["time_control"], "300+0")

        pgn_invalid_elo = pgn.replace("1420", "bad")
        metadata_invalid = extract_pgn_metadata(pgn_invalid_elo, user="alice")
        self.assertIsNone(metadata_invalid["user_rating"])

        empty_metadata = extract_pgn_metadata("invalid", user="alice")
        self.assertEqual(empty_metadata, {"user_rating": None, "time_control": None})

    def test_latest_timestamp_handles_mixed_inputs(self) -> None:
        rows = [
            {"last_timestamp_ms": "20"},
            {"last_timestamp_ms": 5.5},
            {"last_timestamp_ms": True},
            {"last_timestamp_ms": "bad"},
            {"last_timestamp_ms": {"value": 99}},
        ]

        self.assertEqual(latest_timestamp(rows), 20)


if __name__ == "__main__":
    unittest.main()
