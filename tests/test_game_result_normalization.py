from __future__ import annotations

from io import StringIO
import unittest

import chess.pgn

from tactix._get_game_result_for_user_from_pgn_headers import (
    _get_game_result_for_user_from_pgn_headers,
)
from tactix.build_games_table_row__pipeline import _build_games_table_row
from tactix.chess_game_result import ChessGameResult


class GameResultNormalizationTests(unittest.TestCase):
    def test_get_game_result_maps_basic_outcomes(self) -> None:
        cases = [
            ("white_player", "black_player", "1-0", "white_player", ChessGameResult.WIN),
            ("white_player", "black_player", "1-0", "black_player", ChessGameResult.LOSS),
            ("white_player", "black_player", "0-1", "black_player", ChessGameResult.WIN),
            ("white_player", "black_player", "1/2-1/2", "white_player", ChessGameResult.DRAW),
            ("white_player", "black_player", "*", "white_player", ChessGameResult.UNKNOWN),
        ]

        for white, black, result, user, expected in cases:
            with self.subTest(result=result, user=user):
                headers = _headers_for_result(white, black, result)
                resolved = _get_game_result_for_user_from_pgn_headers(headers, user)
                self.assertEqual(resolved, expected)

    def test_build_games_row_normalizes_result_values(self) -> None:
        cases = [
            ("chesscom", "opponent", "1-0", "chesscom", "win"),
            ("opponent", "chesscom", "0-1", "chesscom", "win"),
            ("chesscom", "opponent", "1/2-1/2", "chesscom", "draw"),
            ("chesscom", "opponent", "*", "chesscom", "unknown"),
        ]

        for white, black, result, user, expected in cases:
            with self.subTest(result=result, expected=expected):
                row = _build_games_table_row(
                    {
                        "game_id": "fixture-game",
                        "source": "fixture",
                        "user": user,
                        "pgn": _pgn_with_result(white, black, result),
                        "fetched_at": None,
                        "ingested_at": None,
                        "last_timestamp_ms": None,
                        "cursor": None,
                    }
                )
                self.assertEqual(row.get("result"), expected)


def _headers_for_result(white: str, black: str, result: str) -> chess.pgn.Headers:
    pgn = _pgn_with_result(white, black, result)
    headers = chess.pgn.read_headers(StringIO(pgn))
    if headers is None:
        raise AssertionError("Failed to parse PGN headers for result test")
    return headers


def _pgn_with_result(white: str, black: str, result: str) -> str:
    return (
        '[Event "Fixture"]\n'
        '[Site "https://example.com"]\n'
        '[Date "2024.07.01"]\n'
        f'[White "{white}"]\n'
        f'[Black "{black}"]\n'
        '[TimeControl "60"]\n'
        f'[Result "{result}"]\n\n'
        f"1. e4 e5 {result}\n"
    )
