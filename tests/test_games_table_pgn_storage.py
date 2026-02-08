from __future__ import annotations

from pathlib import Path

from tactix.build_games_table_row__pipeline import _build_games_table_row
from tactix.pgn_utils import split_pgn_chunks


def test_games_table_row_keeps_pgn_text() -> None:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "chesscom_bullet_sample.pgn"
    pgn = split_pgn_chunks(fixture_path.read_text(encoding="utf-8"))[0]
    row = _build_games_table_row(
        {
            "game_id": "fixture-game",
            "source": "chesscom",
            "user": "chesscom",
            "pgn": pgn,
            "fetched_at": None,
            "ingested_at": None,
            "last_timestamp_ms": None,
            "cursor": None,
        }
    )
    assert isinstance(row["pgn"], str)
    assert row["pgn"].strip() != ""
    assert row["pgn"] == pgn
