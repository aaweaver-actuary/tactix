import chess

from tactix.tactic_detectors import BaseTacticDetector


def test_iter_unchanged_sliders_yields_static_slider() -> None:
    board_before = chess.Board("8/8/8/8/8/8/4P3/R3K2k w - - 0 1")
    board_after = board_before.copy()
    board_after.push(chess.Move.from_uci("e2e4"))

    sliders = list(
        BaseTacticDetector.iter_unchanged_sliders(
            board_before,
            board_after,
            mover_color=chess.WHITE,
        )
    )

    assert len(sliders) == 1
    square, piece = sliders[0]
    assert square == chess.A1
    assert piece.piece_type == chess.ROOK


def test_iter_unchanged_sliders_excludes_square() -> None:
    board_before = chess.Board("8/8/8/8/8/8/4P3/R3K2k w - - 0 1")
    board_after = board_before.copy()
    board_after.push(chess.Move.from_uci("a1a3"))

    sliders = list(
        BaseTacticDetector.iter_unchanged_sliders(
            board_before,
            board_after,
            mover_color=chess.WHITE,
            exclude_square=chess.A3,
        )
    )

    assert sliders == []
