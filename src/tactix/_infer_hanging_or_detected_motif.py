from collections.abc import Iterable

import chess

from tactix._is_new_hanging_piece import _is_new_hanging_piece
from tactix.analyze_tactics__positions import MOTIF_DETECTORS
from tactix.detect_tactics__motifs import BaseTacticDetector
from tactix.utils.logger import funclogger


def _capture_square_for_move(
    board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if mover_color == chess.WHITE else 8)
    return move.to_square


def _resolve_checkmate_capture_motif(
    motif_board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> str:
    capture_square = _capture_square_for_move(motif_board, move, mover_color)
    captured_piece = motif_board.piece_at(capture_square)
    if captured_piece is None:
        return "mate"
    is_high_value = BaseTacticDetector.piece_value(
        captured_piece.piece_type
    ) >= BaseTacticDetector.piece_value(chess.ROOK)
    is_undefended = not motif_board.is_attacked_by(not mover_color, capture_square)
    return "hanging_piece" if is_high_value and is_undefended else "mate"


def _resolve_capture_motif(
    motif_board: chess.Board,
    user_board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> str | None:
    if not motif_board.is_capture(move):
        return None
    if user_board.is_checkmate():
        return _resolve_checkmate_capture_motif(motif_board, move, mover_color)
    if BaseTacticDetector.is_hanging_capture(motif_board, user_board, move, mover_color):
        return "hanging_piece"
    return None


def _resolve_initiative_hanging_piece(
    motif: str,
    motif_board: chess.Board,
    user_board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> str | None:
    if motif != "initiative" or not _is_new_hanging_piece(motif_board, user_board, mover_color):
        return None
    attacks = user_board.attacks(move.to_square)
    has_hanging_attack = any(
        _is_hanging_attack(user_board, mover_color, square, attacks)
        for square in _iter_opponent_squares(user_board, mover_color)
    )
    return "hanging_piece" if has_hanging_attack else None


def _is_hanging_attack(
    user_board: chess.Board,
    mover_color: bool,
    square: chess.Square,
    attacks: chess.SquareSet,
) -> bool:
    if square not in attacks:
        return False
    return user_board.is_attacked_by(mover_color, square) and not user_board.is_attacked_by(
        not mover_color, square
    )


def _iter_opponent_squares(
    board: chess.Board,
    mover_color: bool,
) -> Iterable[chess.Square]:
    for square, piece in board.piece_map().items():
        if piece.color != mover_color:
            yield square


@funclogger
def _infer_hanging_or_detected_motif(
    motif_board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> str:
    user_board = motif_board.copy()
    user_board.push(move)
    result = _resolve_capture_motif(motif_board, user_board, move, mover_color)
    if result is not None:
        return result
    if user_board.is_checkmate():
        return "mate"
    motif = MOTIF_DETECTORS.infer_motif(motif_board, move)
    return (
        _resolve_initiative_hanging_piece(
            motif,
            motif_board,
            user_board,
            move,
            mover_color,
        )
        or motif
    )
