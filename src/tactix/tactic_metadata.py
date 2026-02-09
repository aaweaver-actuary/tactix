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


def resolve_tactic_metadata(
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


def _resolve_tactic_piece(  # noqa: PLR0911
    fen: str | None,
    best_uci: str,
    best_san: str | None,
) -> str | None:
    if best_san:
        if best_san.startswith("O-O"):
            return "king"
        if best_san and best_san[0] in _SAN_PIECE_LABELS:
            return _SAN_PIECE_LABELS[best_san[0]]
    if not fen or not best_uci:
        return None
    try:
        board = chess.Board(str(fen))
        move = chess.Move.from_uci(best_uci)
        if move not in board.legal_moves:
            return None
        piece = board.piece_at(move.from_square)
        if piece is None:
            return None
        return _PIECE_TYPE_LABELS.get(piece.piece_type)
    except (ValueError, AssertionError):
        return None


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
    if _is_smothered(context):
        return "smothered"
    if _is_back_rank(context):
        return "back_rank"
    if _is_dovetail(context):
        return "dovetail"
    helper_piece = _helper_piece(context)
    if helper_piece is None:
        return "other"
    return f"helper_{helper_piece}"


def _build_mate_context(fen: str, best_uci: str) -> _MateContext | None:  # noqa: PLR0911
    try:
        board_before = chess.Board(str(fen))
        move = chess.Move.from_uci(best_uci)
    except (ValueError, AssertionError):
        return None
    if move not in board_before.legal_moves:
        return None
    move_piece = board_before.piece_at(move.from_square)
    if move_piece is None:
        return None
    mover_color = board_before.turn
    defender_color = not mover_color
    board_after = board_before.copy()
    board_after.push(move)
    if not board_after.is_checkmate():
        return None
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
    occupied_by_defender = sum(
        1
        for square in adjacent
        if (piece := context.board_after.piece_at(square)) and piece.color == context.defender_color
    )
    if not adjacent:
        return False
    return occupied_by_defender >= max(2, len(adjacent) - 1)


def _is_back_rank(context: _MateContext) -> bool:
    if context.move_piece_type not in {chess.ROOK, chess.QUEEN}:
        return False
    king_rank = chess.square_rank(context.king_square)
    expected_king_rank = 0 if context.defender_color == chess.WHITE else 7
    if king_rank != expected_king_rank:
        return False
    pawn_rank = 1 if context.defender_color == chess.WHITE else 6
    king_file = chess.square_file(context.king_square)
    pawn_wall = 0
    for file_delta in (-1, 0, 1):
        file_value = king_file + file_delta
        if file_value < 0 or file_value > _BOARD_LAST_FILE:
            continue
        square = chess.square(file_value, pawn_rank)
        piece = context.board_before.piece_at(square)
        if piece and piece.color == context.defender_color and piece.piece_type == chess.PAWN:
            pawn_wall += 1
    return pawn_wall >= _BACK_RANK_PAWN_WALL_MIN


def _is_dovetail(context: _MateContext) -> bool:
    if context.move_piece_type != chess.QUEEN:
        return False
    if not _is_corner_square(context.king_square):
        return False
    if chess.square_distance(context.move.to_square, context.king_square) != 1:
        return False
    adjacent = chess.SquareSet(chess.BB_KING_ATTACKS[context.king_square])
    defender_blocks = 0
    for square in adjacent:
        if square == context.move.to_square:
            continue
        piece = context.board_after.piece_at(square)
        if piece and piece.color == context.defender_color:
            defender_blocks += 1
    return defender_blocks >= 1


def _is_corner_square(square: chess.Square) -> bool:
    return square in {chess.A1, chess.A8, chess.H1, chess.H8}


def _helper_piece(context: _MateContext) -> str | None:
    helpers: set[int] = set()
    attackers = context.board_after.attackers(context.mover_color, context.move.to_square)
    for attacker_square in attackers:
        piece = context.board_after.piece_at(attacker_square)
        if piece is None or piece.color != context.mover_color:
            continue
        helpers.add(piece.piece_type)
    for piece_type in _HELPER_PRIORITY:
        if piece_type in helpers:
            return _PIECE_TYPE_LABELS.get(piece_type)
    return None


__all__ = ["resolve_tactic_metadata"]
