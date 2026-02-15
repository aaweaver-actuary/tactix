from tactix.analyze_position import (
    _coerce_post_move_text,
    _parse_post_move_inputs,
    _safe_board_from_fen,
)


def test_coerce_post_move_text_empty_values() -> None:
    assert _coerce_post_move_text(None) is None
    assert _coerce_post_move_text("") is None


def test_safe_board_from_fen_invalid() -> None:
    assert _safe_board_from_fen("bad fen") is None


def test_parse_post_move_inputs_missing_uci() -> None:
    result = _parse_post_move_inputs({"fen": "8/8/8/8/8/8/8/8 w - - 0 1"})
    assert result is None
