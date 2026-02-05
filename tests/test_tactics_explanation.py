import chess

from tactix.format_tactics__explanation import format_tactic_explanation


def test_format_tactic_explanation_with_fen_and_legal_move() -> None:
    fen = chess.STARTING_FEN
    best_san, explanation = format_tactic_explanation(fen, "e2e4", "fork")

    assert best_san == "e4"
    assert explanation == "fork tactic. Best line: e4."


def test_format_tactic_explanation_with_invalid_move() -> None:
    fen = chess.STARTING_FEN
    best_san, explanation = format_tactic_explanation(fen, "e2e5", "pin")

    assert best_san is None
    assert explanation == "pin tactic. Best line: e2e5."


def test_format_tactic_explanation_without_fen() -> None:
    best_san, explanation = format_tactic_explanation(None, "g1f3", None)

    assert best_san is None
    assert explanation == "tactic tactic. Best line: g1f3."


def test_format_tactic_explanation_without_best_move() -> None:
    best_san, explanation = format_tactic_explanation(chess.STARTING_FEN, "", "fork")

    assert best_san is None
    assert explanation is None


def test_format_tactic_explanation_with_invalid_fen() -> None:
    best_san, explanation = format_tactic_explanation("invalid", "e2e4", "fork")

    assert best_san is None
    assert explanation == "fork tactic. Best line: e2e4."
