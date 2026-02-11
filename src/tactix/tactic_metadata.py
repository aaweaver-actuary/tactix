"""Resolve tactic metadata fields such as piece labels and mate type."""

from __future__ import annotations

from dataclasses import dataclass

import chess

from tactix._best_san_from_fen import _best_san_from_fen

_SAN_PIECE_LABELS = {
    "N": "knight",
    "B": "bishop",
    "R": "rook",
    "Q": "queen",
    "K": "king",
}

_PIECE_TYPE_LABELS = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}

_HELPER_PRIORITY = (
    chess.PAWN,
    chess.KNIGHT,
    chess.BISHOP,
    chess.ROOK,
    chess.KING,
    chess.QUEEN,
)

_BOARD_LAST_FILE = 7
_BACK_RANK_PAWN_WALL_MIN = 2


@dataclass(frozen=True)
class _MateContext:
    board_before: chess.Board
    board_after: chess.Board
    move: chess.Move
    mover_color: bool
    defender_color: bool
    move_piece_type: int
    king_square: chess.Square


def resolve_tactic_metadata(  # pragma: no cover
    fen: str | None,
    best_uci: str | None,
    motif: str | None,
) -> dict[str, str | None]:
    """Return metadata fields used to enrich tactic persistence."""
    best_uci_value = (best_uci or "").strip()
    best_san = _best_san_from_fen(fen, best_uci_value) if best_uci_value else None
    tactic_piece = _resolve_tactic_piece(fen, best_uci_value, best_san)
    mate_type = _resolve_mate_type(fen, best_uci_value, motif)
    return {
        "tactic_piece": tactic_piece,
        "mate_type": mate_type,
    }


# pylint: disable=too-many-return-statements
def _resolve_tactic_piece(  # noqa: PLR0911
    fen: str | None,
    best_uci: str,
    best_san: str | None,
) -> str | None:
    san_piece = _tactic_piece_from_san(best_san)
    if san_piece is not None:
        return san_piece
    return _tactic_piece_from_fen(fen, best_uci)


def _resolve_mate_type(  # noqa: PLR0911
    fen: str | None,
    best_uci: str,
    motif: str | None,
) -> str | None:
    if motif != "mate" or not fen or not best_uci:
        return None
    context = _build_mate_context(fen, best_uci)
    if context is None:
        return None
    return _resolve_mate_type_from_context(context)


# pylint: enable=too-many-return-statements


def _build_mate_context(fen: str, best_uci: str) -> _MateContext | None:  # noqa: PLR0911
    parsed = _parse_mate_inputs(fen, best_uci)
    if parsed is None:
        return None
    board_before, move = parsed
    move_piece = board_before.piece_at(move.from_square)
    if move_piece is None:
        return None
    board_after = _apply_mate_move(board_before, move)
    if board_after is None:
        return None
    mover_color = board_before.turn
    defender_color = not mover_color
    king_square = board_after.king(defender_color)
    if king_square is None:
        return None
    return _MateContext(
        board_before=board_before,
        board_after=board_after,
        move=move,
        mover_color=mover_color,
        defender_color=defender_color,
        move_piece_type=move_piece.piece_type,
        king_square=king_square,
    )


def _is_smothered(context: _MateContext) -> bool:
    if context.move_piece_type != chess.KNIGHT:
        return False
    adjacent = chess.SquareSet(chess.BB_KING_ATTACKS[context.king_square])
    if not adjacent:
        return False
    occupied_by_defender = _count_adjacent_defenders(context, adjacent)
    return occupied_by_defender >= max(2, len(adjacent) - 1)


def _is_back_rank(context: _MateContext) -> bool:
    if context.move_piece_type not in {chess.ROOK, chess.QUEEN}:
        return False
    king_rank = chess.square_rank(context.king_square)
    expected_king_rank = 0 if context.defender_color == chess.WHITE else 7
    if king_rank != expected_king_rank:
        return False
    pawn_wall = _back_rank_pawn_wall(context)
    return pawn_wall >= _BACK_RANK_PAWN_WALL_MIN


def _is_dovetail(context: _MateContext) -> bool:
    if context.move_piece_type != chess.QUEEN:
        return False
    if not _is_corner_square(context.king_square):
        return False
    if chess.square_distance(context.move.to_square, context.king_square) != 1:
        return False
    defender_blocks = _count_dovetail_blocks(context)
    return defender_blocks >= 1


def _is_corner_square(square: chess.Square) -> bool:
    return square in {chess.A1, chess.A8, chess.H1, chess.H8}


def _helper_piece(context: _MateContext) -> str | None:
    helpers = _collect_helper_piece_types(context)
    return _first_helper_label(helpers)


def _tactic_piece_from_san(best_san: str | None) -> str | None:
    if not best_san:
        return None
    if best_san.startswith("O-O"):
        return "king"
    san_key = best_san[0]
    return _SAN_PIECE_LABELS.get(san_key)


def _tactic_piece_from_fen(fen: str | None, best_uci: str) -> str | None:
    parsed = _parse_board_and_move_from_fen(fen, best_uci)
    if parsed is None:
        return None
    board, move = parsed
    return _piece_label_from_move(board, move)


def _resolve_mate_type_from_context(context: _MateContext) -> str | None:
    for matcher, label in (
        (_is_smothered, "smothered"),
        (_is_back_rank, "back_rank"),
        (_is_dovetail, "dovetail"),
    ):
        if matcher(context):
            return label
    return _helper_mate_type(context)


def _helper_mate_type(context: _MateContext) -> str:
    helper_piece = _helper_piece(context)
    if helper_piece is None:
        return "other"
    return f"helper_{helper_piece}"


def _parse_mate_inputs(fen: str, best_uci: str) -> tuple[chess.Board, chess.Move] | None:
    try:
        board_before = chess.Board(str(fen))
        move = chess.Move.from_uci(best_uci)
    except (ValueError, AssertionError):
        return None
    if move not in board_before.legal_moves:
        return None
    return board_before, move


def _apply_mate_move(board_before: chess.Board, move: chess.Move) -> chess.Board | None:
    board_after = board_before.copy()
    board_after.push(move)  # pylint: disable=no-member
    if not board_after.is_checkmate():  # pylint: disable=no-member
        return None
    return board_after


def _count_adjacent_defenders(context: _MateContext, adjacent: chess.SquareSet) -> int:
    count = 0
    for square in adjacent:
        piece = context.board_after.piece_at(square)
        if piece and piece.color == context.defender_color:
            count += 1
    return count


def _back_rank_pawn_wall(context: _MateContext) -> int:
    pawn_rank = 1 if context.defender_color == chess.WHITE else 6
    pawn_files = _pawn_wall_files(context.king_square)
    return sum(
        1 for file_value in pawn_files if _is_defender_pawn_at(context, file_value, pawn_rank)
    )


def _count_dovetail_blocks(context: _MateContext) -> int:
    adjacent = chess.SquareSet(chess.BB_KING_ATTACKS[context.king_square])
    defender_blocks = 0
    for square in adjacent:
        if square == context.move.to_square:
            continue
        piece = context.board_after.piece_at(square)
        if piece and piece.color == context.defender_color:
            defender_blocks += 1
    return defender_blocks


def _collect_helper_piece_types(context: _MateContext) -> set[int]:
    helpers: set[int] = set()
    attackers = context.board_after.attackers(context.mover_color, context.move.to_square)
    for attacker_square in attackers:
        piece = context.board_after.piece_at(attacker_square)
        if piece is None or piece.color != context.mover_color:
            continue
        helpers.add(piece.piece_type)
    return helpers


def _first_helper_label(helpers: set[int]) -> str | None:
    for piece_type in _HELPER_PRIORITY:
        if piece_type in helpers:
            return _PIECE_TYPE_LABELS.get(piece_type)
    return None


def _parse_board_and_move_from_fen(
    fen: str | None,
    best_uci: str,
) -> tuple[chess.Board, chess.Move] | None:
    if not fen or not best_uci:
        return None
    try:
        board = chess.Board(str(fen))
        move = chess.Move.from_uci(best_uci)
    except (ValueError, AssertionError):
        return None
    if move not in board.legal_moves:
        return None
    return board, move


def _piece_label_from_move(board: chess.Board, move: chess.Move) -> str | None:
    piece = board.piece_at(move.from_square)
    if piece is None:
        return None
    return _PIECE_TYPE_LABELS.get(piece.piece_type)


def _pawn_wall_files(king_square: chess.Square) -> list[int]:
    king_file = chess.square_file(king_square)
    return [
        file_value
        for file_value in (king_file - 1, king_file, king_file + 1)
        if 0 <= file_value <= _BOARD_LAST_FILE
    ]


def _is_defender_pawn_at(
    context: _MateContext,
    file_value: int,
    pawn_rank: int,
) -> bool:
    square = chess.square(file_value, pawn_rank)
    piece = context.board_before.piece_at(square)
    return (
        piece is not None
        and piece.color == context.defender_color
        and piece.piece_type == chess.PAWN
    )


__all__ = ["resolve_tactic_metadata"]
