from pathlib import Path
import unittest

from tactix.build_games_table_row__pipeline import _build_games_table_row
from tactix.chess_time_control import normalize_time_control_label
from tactix.pgn_utils import split_pgn_chunks


class TimeControlNormalizationTests(unittest.TestCase):
    def test_normalize_time_control_label(self) -> None:
        cases = {
            None: "unknown",
            "": "unknown",
            "-": "unknown",
            "bullet": "bullet",
            "Rapid": "rapid",
            "correspondence": "classical",
            "60": "bullet",
            "180": "bullet",
            "300": "blitz",
            "300+3": "blitz",
            "600": "rapid",
            "600+5": "rapid",
            "1800": "classical",
            "1800+0": "classical",
            "1/259200": "classical",
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(normalize_time_control_label(value), expected)

    def test_build_games_row_normalizes_fixture_time_controls(self) -> None:
        fixtures = {
            "chesscom_bullet_sample.pgn": "bullet",
            "chesscom_blitz_sample.pgn": "blitz",
            "chesscom_rapid_sample.pgn": "rapid",
            "chesscom_classical_sample.pgn": "classical",
            "chesscom_correspondence_sample.pgn": "classical",
            "lichess_bullet_sample.pgn": "bullet",
            "lichess_blitz_sample.pgn": "blitz",
            "lichess_rapid_sample.pgn": "rapid",
            "lichess_classical_sample.pgn": "classical",
            "lichess_correspondence_sample.pgn": "classical",
        }

        for filename, expected in fixtures.items():
            with self.subTest(filename=filename):
                pgn = _first_pgn(Path(__file__).resolve().parent / "fixtures" / filename)
                row = _build_games_table_row(
                    {
                        "game_id": "fixture-game",
                        "source": "fixture",
                        "user": "fixture",
                        "pgn": pgn,
                        "fetched_at": None,
                        "ingested_at": None,
                        "last_timestamp_ms": None,
                        "cursor": None,
                    }
                )
                self.assertEqual(row.get("time_control"), expected)


def _first_pgn(path: Path) -> str:
    chunks = split_pgn_chunks(path.read_text(encoding="utf-8"))
    if not chunks:
        raise AssertionError(f"No PGN chunks found in {path}")
    return chunks[0]
