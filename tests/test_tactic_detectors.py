import chess

from tactix.detect_tactics__motifs import BaseTacticDetector


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


def test_is_hanging_capture_exchange_is_favorable() -> None:
    board_before = chess.Board("3qk3/8/8/8/3p4/4PN2/8/4K3 w - - 0 1")
    move = chess.Move.from_uci("f3d4")
    board_after = board_before.copy()
    board_after.push(move)

    assert BaseTacticDetector.is_hanging_capture(
        board_before,
        board_after,
        move,
        mover_color=chess.WHITE,
    )


def test_is_hanging_capture_ignores_checkmate_positions() -> None:
    board_before = chess.Board("7k/6Qr/7K/8/8/8/8/8 w - - 0 1")
    move = chess.Move.from_uci("g7h7")
    board_after = board_before.copy()
    board_after.push(move)

    assert board_after.is_checkmate()
    assert not BaseTacticDetector.is_hanging_capture(
        board_before,
        board_after,
        move,
        mover_color=chess.WHITE,
    )
