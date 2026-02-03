from __future__ import annotations

from pathlib import Path

from tactix.pgn_headers import PgnHeaders


def _sample_pgn() -> str:
    return (
        '[Event "Live Chess"]\n'
        '[Site "https://chess.com/game/live/123456"]\n'
        '[Date "2026.02.01"]\n'
        '[Round "2"]\n'
        '[White "white_user"]\n'
        '[Black "black_user"]\n'
        '[Result "1-0"]\n'
        '[WhiteElo "1500"]\n'
        '[BlackElo "1490"]\n'
        '[TimeControl "120+1"]\n'
        '[Termination "Normal"]\n\n'
        "1. e4 e5 2. Nf3 Nc6 1-0\n"
    )


def test_pgn_headers_from_pgn_string_parses_fields() -> None:
    headers = PgnHeaders.from_pgn_string(_sample_pgn())
    assert headers.event == "Live Chess"
    assert headers.site == "https://chess.com/game/live/123456"
    assert headers.round == 2
    assert headers.white_player == "white_user"
    assert headers.black_player == "black_user"
    assert headers.white_elo == 1500
    assert headers.black_elo == 1490
    assert headers.time_control.initial == 120
    assert headers.time_control.increment == 1
    assert headers.termination == "Normal"
    assert headers.date.year == 2026


def test_pgn_headers_from_pgn_string_handles_missing_headers() -> None:
    headers = PgnHeaders.from_pgn_string("invalid")
    assert headers.event == ""
    assert headers.site == ""
    assert headers.round is None


def test_pgn_headers_extract_all_from_str_splits_games() -> None:
    combined = _sample_pgn() + "\n" + _sample_pgn().replace("123456", "654321")
    headers_list = PgnHeaders.extract_all_from_str(combined)
    assert len(headers_list) == 2
    assert headers_list[0].site.endswith("123456")
    assert headers_list[1].site.endswith("654321")


def test_pgn_headers_from_file(tmp_path: Path) -> None:
    pgn_path = tmp_path / "game.pgn"
    pgn_path.write_text(_sample_pgn(), encoding="utf-8")
    headers = PgnHeaders.from_file(str(pgn_path))
    assert headers.site.endswith("123456")
