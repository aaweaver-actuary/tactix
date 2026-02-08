from __future__ import annotations

from pathlib import Path
import unittest

from tactix.build_games_table_row__pipeline import _build_games_table_row
from tactix.pgn_utils import split_pgn_chunks


class UserColorInferenceTests(unittest.TestCase):
    def test_build_games_row_infers_fixture_user_color(self) -> None:
        path = Path(__file__).resolve().parent / "fixtures" / "chesscom_bullet_sample.pgn"
        chunks = split_pgn_chunks(path.read_text(encoding="utf-8"))
        cases = [(chunks[0], "white"), (chunks[1], "black")]

        for pgn, expected in cases:
            with self.subTest(expected=expected):
                row = _build_games_table_row(
                    {
                        "game_id": "fixture-game",
                        "source": "fixture",
                        "user": "chesscom",
                        "pgn": pgn,
                        "fetched_at": None,
                        "ingested_at": None,
                        "last_timestamp_ms": None,
                        "cursor": None,
                    }
                )
                self.assertEqual(row.get("user_color"), expected)

    def test_build_games_row_infers_user_color_with_annotations(self) -> None:
        white_pgn = _pgn_with_players("ChessCom (1500)", "Opponent", "1-0")
        black_pgn = _pgn_with_players("Opponent", "ChessCom (1500)", "0-1")
        cases = [(white_pgn, "white"), (black_pgn, "black")]

        for pgn, expected in cases:
            with self.subTest(expected=expected):
                row = _build_games_table_row(
                    {
                        "game_id": "fixture-game",
                        "source": "fixture",
                        "user": "chesscom",
                        "pgn": pgn,
                        "fetched_at": None,
                        "ingested_at": None,
                        "last_timestamp_ms": None,
                        "cursor": None,
                    }
                )
                self.assertEqual(row.get("user_color"), expected)


def _pgn_with_players(white: str, black: str, result: str) -> str:
    return (
        '[Event "Fixture"]\n'
        '[Site "https://example.com"]\n'
        '[Date "2024.07.01"]\n'
        f'[White "{white}"]\n'
        f'[Black "{black}"]\n'
        '[TimeControl "60"]\n'
        f'[Result "{result}"]\n\n'
        "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0\n"
    )
