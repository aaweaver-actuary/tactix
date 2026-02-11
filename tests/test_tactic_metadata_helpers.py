from unittest.mock import MagicMock, patch

import chess

from tactix import tactic_metadata as tm


def _make_context(
    board_after: chess.Board,
    *,
    move: chess.Move,
    mover_color: bool,
    defender_color: bool,
    move_piece_type: int,
    king_square: chess.Square,
) -> tm._MateContext:
    return tm._MateContext(
        board_before=board_after.copy(),
        board_after=board_after,
        move=move,
        mover_color=mover_color,
        defender_color=defender_color,
        move_piece_type=move_piece_type,
        king_square=king_square,
    )


def test_resolve_mate_type_returns_none_for_non_mate() -> None:
    assert tm._resolve_mate_type(None, "", "hanging_piece") is None


def test_resolve_tactic_metadata_returns_shape() -> None:
    fen = "r6k/8/8/8/8/8/8/R6K w - - 0 1"
    payload = tm.resolve_tactic_metadata(fen, "a1a8", "hanging_piece")

    assert set(payload.keys()) == {"tactic_piece", "mate_type"}


def test_resolve_mate_type_returns_none_for_invalid_context() -> None:
    assert tm._resolve_mate_type("bad fen", "e2e4", "mate") is None


def test_build_mate_context_returns_none_for_bad_inputs() -> None:
    assert tm._build_mate_context("bad fen", "e2e4") is None


def test_build_mate_context_returns_none_when_move_piece_missing() -> None:
    board = chess.Board("7k/8/8/8/8/8/8/7K w - - 0 1")
    move = chess.Move.from_uci("a1a2")
    with patch("tactix.tactic_metadata._parse_mate_inputs", return_value=(board, move)):
        assert tm._build_mate_context("ignored", "ignored") is None


def test_build_mate_context_returns_none_when_move_not_mate() -> None:
    board = chess.Board("7k/8/8/8/8/8/8/7K w - - 0 1")
    move = chess.Move.from_uci("h1h2")
    with (
        patch("tactix.tactic_metadata._parse_mate_inputs", return_value=(board, move)),
        patch("tactix.tactic_metadata._apply_mate_move", return_value=None),
    ):
        assert tm._build_mate_context("ignored", "ignored") is None


def test_build_mate_context_returns_none_when_king_missing() -> None:
    board = chess.Board("7k/8/8/8/8/8/8/7K w - - 0 1")
    move = chess.Move.from_uci("h1h2")
    board_after = MagicMock()
    board_after.king.return_value = None
    with (
        patch("tactix.tactic_metadata._parse_mate_inputs", return_value=(board, move)),
        patch("tactix.tactic_metadata._apply_mate_move", return_value=board_after),
    ):
        assert tm._build_mate_context("ignored", "ignored") is None


def test_parse_mate_inputs_rejects_illegal_move() -> None:
    fen = "7k/8/8/8/8/8/8/7K w - - 0 1"
    assert tm._parse_mate_inputs(fen, "a1a8") is None


def test_parse_mate_inputs_rejects_invalid_uci() -> None:
    fen = "7k/8/8/8/8/8/8/7K w - - 0 1"
    assert tm._parse_mate_inputs(fen, "bad") is None


def test_apply_mate_move_returns_none_when_not_checkmate() -> None:
    board = chess.Board()
    move = chess.Move.from_uci("e2e4")
    assert tm._apply_mate_move(board, move) is None


def test_is_smothered_detects_defender_wall() -> None:
    board = chess.Board("7k/6pp/8/8/8/8/8/6N1 w - - 0 1")
    context = _make_context(
        board,
        move=chess.Move.from_uci("g1h3"),
        mover_color=chess.WHITE,
        defender_color=chess.BLACK,
        move_piece_type=chess.KNIGHT,
        king_square=chess.H8,
    )
    assert tm._is_smothered(context)


def test_is_smothered_returns_false_for_empty_adjacent() -> None:
    board = chess.Board("7k/6pp/8/8/8/8/8/6N1 w - - 0 1")
    context = _make_context(
        board,
        move=chess.Move.from_uci("g1h3"),
        mover_color=chess.WHITE,
        defender_color=chess.BLACK,
        move_piece_type=chess.KNIGHT,
        king_square=chess.A1,
    )
    empty_attacks = list(chess.BB_KING_ATTACKS)
    empty_attacks[chess.A1] = 0
    with patch("tactix.tactic_metadata.chess.BB_KING_ATTACKS", empty_attacks):
        assert not tm._is_smothered(context)


def test_is_back_rank_detects_pawn_wall() -> None:
    board = chess.Board("6k1/5ppp/8/8/8/8/8/6R1 w - - 0 1")
    context = _make_context(
        board,
        move=chess.Move.from_uci("g1g8"),
        mover_color=chess.WHITE,
        defender_color=chess.BLACK,
        move_piece_type=chess.ROOK,
        king_square=chess.G8,
    )
    assert tm._is_back_rank(context)


def test_is_dovetail_detects_corner_blocks() -> None:
    board = chess.Board("6rk/6Qp/8/8/8/8/8/7K w - - 0 1")
    context = _make_context(
        board,
        move=chess.Move.from_uci("g7g8"),
        mover_color=chess.WHITE,
        defender_color=chess.BLACK,
        move_piece_type=chess.QUEEN,
        king_square=chess.H8,
    )
    assert tm._is_dovetail(context)


def test_is_dovetail_false_outside_corner() -> None:
    board = chess.Board("6k1/6Qp/8/8/8/8/8/7K w - - 0 1")
    context = _make_context(
        board,
        move=chess.Move.from_uci("g7g8"),
        mover_color=chess.WHITE,
        defender_color=chess.BLACK,
        move_piece_type=chess.QUEEN,
        king_square=chess.G8,
    )
    assert not tm._is_dovetail(context)


def test_tactic_piece_from_san_handles_castle_and_knight() -> None:
    assert tm._tactic_piece_from_san("O-O") == "king"
    assert tm._tactic_piece_from_san("Nf3") == "knight"


def test_tactic_piece_from_san_handles_empty() -> None:
    assert tm._tactic_piece_from_san(None) is None


def test_tactic_piece_from_fen_resolves_piece() -> None:
    fen = "r6k/8/8/8/8/8/8/R6K w - - 0 1"
    assert tm._tactic_piece_from_fen(fen, "a1a8") == "rook"


def test_tactic_piece_from_fen_rejects_missing_inputs() -> None:
    assert tm._tactic_piece_from_fen(None, "") is None


def test_parse_board_and_move_from_fen_rejects_invalid_inputs() -> None:
    assert tm._parse_board_and_move_from_fen(None, "e2e4") is None
    assert tm._parse_board_and_move_from_fen("7k/8/8/8/8/8/8/7K w - - 0 1", "bad") is None
    assert (
        tm._parse_board_and_move_from_fen(
            "7k/8/8/8/8/8/8/7K w - - 0 1",
            "a1a8",
        )
        is None
    )


def test_piece_label_from_move_returns_none_for_empty_square() -> None:
    board = chess.Board("7k/8/8/8/8/8/8/7K w - - 0 1")
    move = chess.Move.from_uci("a1a2")
    assert tm._piece_label_from_move(board, move) is None


def test_collect_helper_piece_types_skips_missing_piece() -> None:
    board_after = MagicMock()
    board_after.attackers.return_value = [chess.A1]
    board_after.piece_at.return_value = None
    context = tm._MateContext(
        board_before=MagicMock(),
        board_after=board_after,
        move=chess.Move.from_uci("a2a3"),
        mover_color=chess.WHITE,
        defender_color=chess.BLACK,
        move_piece_type=chess.QUEEN,
        king_square=chess.A1,
    )
    assert tm._collect_helper_piece_types(context) == set()
