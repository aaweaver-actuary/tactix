from __future__ import annotations

import chess

from tactix.BaseTacticDetector import (
    BaseTacticDetector,
    _can_compare_capture,
    _captured_piece_for_move,
    _is_favorable_exchange_capture,
    _is_favorable_trade,
    _is_favorable_trade_on_square,
    _is_hanging_piece_on_square,
    _is_slider_candidate,
    _is_unchanged_slider,
    _is_undefended_capture,
    _iter_unchanged_sliders,
    _legal_capture_attacker_values,
    _simple_exchange_wins,
)


def test_base_tactic_detector_detect_raises() -> None:
    detector = BaseTacticDetector()
    try:
        detector.detect(None)
    except NotImplementedError:
        assert True
    else:
        assert False


def test_slider_helpers_cover_branches() -> None:
    board_before = chess.Board()
    board_after = board_before.copy()
    board_after.push(chess.Move.from_uci("e2e4"))

    mismatch_piece = chess.Piece(chess.BISHOP, chess.WHITE)
    assert _is_unchanged_slider(board_before, chess.A1, mismatch_piece) is False

    rook = board_after.piece_at(chess.A1)
    assert rook is not None
    assert _is_slider_candidate(rook, chess.WHITE, chess.A1, None) is True
    assert _is_slider_candidate(rook, chess.WHITE, chess.A1, chess.A1) is False

    unchanged = list(
        _iter_unchanged_sliders(
            board_before,
            board_after,
            chess.WHITE,
            exclude_square=chess.A1,
        )
    )
    assert any(square != chess.A1 for square, _ in unchanged)


def test_trade_and_attacker_helpers() -> None:
    board = chess.Board("4k3/8/8/8/3p4/4Q3/8/4K3 b - - 0 1")
    target_square = chess.E3
    target_piece = board.piece_at(target_square)
    assert target_piece is not None
    assert (
        _is_favorable_trade_on_square(board, target_square, target_piece, opponent=chess.BLACK)
        is True
    )
    assert (
        BaseTacticDetector.is_favorable_trade_on_square(
            board,
            target_square,
            target_piece,
            chess.BLACK,
        )
        is True
    )

    multi_attack_board = chess.Board("8/8/8/3p4/2B1P3/8/8/4K3 w - - 0 1")
    values = _legal_capture_attacker_values(multi_attack_board, chess.D5)
    assert values == [100, 300]

    miss_board = chess.Board("8/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    assert (
        _is_favorable_trade_on_square(
            miss_board,
            chess.C6,
            chess.Piece(chess.PAWN, chess.BLACK),
            opponent=chess.WHITE,
        )
        is False
    )


def test_exchange_helpers_and_hanging_capture(monkeypatch) -> None:
    board_before = chess.Board("4k3/8/4p3/3p4/2B1P3/8/8/4K3 w - - 0 1")
    move = chess.Move.from_uci("c4d5")
    board_after = board_before.copy()
    board_after.push(move)
    captured_piece = board_before.piece_at(chess.D5)
    assert captured_piece is not None

    assert _captured_piece_for_move(board_before, move, chess.WHITE) == captured_piece
    assert _is_undefended_capture(board_before, move, chess.WHITE) is True
    assert _simple_exchange_wins(board_before, board_after, move, chess.WHITE) is True
    assert (
        _is_favorable_exchange_capture(
            board_before,
            board_after,
            move,
            chess.WHITE,
            captured_piece,
        )
        is True
    )
    monkeypatch.setattr(
        "tactix.BaseTacticDetector._is_undefended_capture",
        lambda *_args, **_kwargs: False,
    )
    assert (
        BaseTacticDetector.is_hanging_capture(
            board_before,
            board_after,
            move,
            chess.WHITE,
        )
        is True
    )
    assert _is_favorable_trade(captured_piece, chess.Piece(chess.BISHOP, chess.WHITE)) is False
    assert _can_compare_capture(None, board_after) is False

    monkeypatch.setattr(
        "tactix.BaseTacticDetector._captured_piece_for_move",
        lambda *_args, **_kwargs: None,
    )
    assert (
        BaseTacticDetector.is_hanging_capture(
            board_before,
            board_after,
            move,
            chess.WHITE,
        )
        is False
    )


def test_hanging_piece_uses_trade_check(monkeypatch) -> None:
    board = chess.Board()
    piece = chess.Piece(chess.QUEEN, chess.WHITE)
    monkeypatch.setattr(
        "tactix.BaseTacticDetector._has_legal_capture_on_square",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "tactix.BaseTacticDetector.BaseTacticDetector.is_favorable_trade_on_square",
        lambda *_args, **_kwargs: True,
    )
    assert _is_hanging_piece_on_square(board, chess.E4, piece, chess.WHITE) is True


def test_high_value_target_helpers() -> None:
    board = chess.Board("4k3/5q2/8/8/2B5/8/8/4K3 w - - 0 1")
    assert BaseTacticDetector.count_high_value_targets(board, chess.C4, chess.WHITE) == 1
    assert BaseTacticDetector.has_high_value_target(board, chess.C4, chess.BLACK) is True
    assert BaseTacticDetector.count_high_value_targets(board, chess.D4, chess.WHITE) == 0
    assert BaseTacticDetector.has_high_value_target(board, chess.D4, chess.BLACK) is False


def test_exchange_helpers_cover_empty_cases(monkeypatch) -> None:
    board_before = chess.Board()
    move = chess.Move.from_uci("e2e4")
    board_after = board_before.copy()
    board_after.push(move)
    assert _simple_exchange_wins(board_before, board_after, move, chess.WHITE) is False

    board_before_capture = chess.Board("4k3/8/8/3p4/2B5/8/8/4K3 w - - 0 1")
    capture_move = chess.Move.from_uci("c4d5")
    board_after_capture = board_before_capture.copy()
    board_after_capture.push(capture_move)
    assert (
        _simple_exchange_wins(
            board_before_capture,
            board_after_capture,
            capture_move,
            chess.WHITE,
        )
        is False
    )

    empty_from_move = chess.Move.from_uci("a3a4")
    assert (
        _is_favorable_exchange_capture(
            board_before,
            board_after,
            empty_from_move,
            chess.WHITE,
            chess.Piece(chess.PAWN, chess.BLACK),
        )
        is False
    )

    monkeypatch.setattr(
        "tactix.BaseTacticDetector._can_compare_capture",
        lambda *_args, **_kwargs: True,
    )
    assert (
        _is_favorable_exchange_capture(
            board_before,
            board_after,
            empty_from_move,
            chess.WHITE,
            chess.Piece(chess.PAWN, chess.BLACK),
        )
        is False
    )

    class FakeBoard:
        def __init__(self) -> None:
            self.legal_moves = [chess.Move.from_uci("e2e4")]
            self.turn = chess.WHITE

        def is_capture(self, _move) -> bool:
            return True

        def piece_at(self, _square):
            return None

    fake_board = FakeBoard()
    monkeypatch.setattr(
        "tactix.BaseTacticDetector._resolve_capture_square__move",
        lambda *_args, **_kwargs: chess.D5,
    )
    assert _legal_capture_attacker_values(fake_board, chess.D5) == []
