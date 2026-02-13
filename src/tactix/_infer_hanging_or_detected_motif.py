from collections.abc import Iterable
from dataclasses import dataclass

import chess

from tactix._is_new_hanging_piece import _is_new_hanging_piece
from tactix._resolve_capture_square__move import _resolve_capture_square__move
from tactix.analyze_tactics__positions import MOTIF_DETECTORS
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.utils.logger import funclogger


def _resolve_checkmate_capture_motif(
    motif_board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> str:
    capture_square = _resolve_capture_square__move(motif_board, move, mover_color)
    captured_piece = motif_board.piece_at(capture_square)
    if captured_piece is None:
        return "mate"
    is_high_value = BaseTacticDetector.piece_value(
        captured_piece.piece_type
    ) >= BaseTacticDetector.piece_value(chess.ROOK)
    return "hanging_piece" if is_high_value else "mate"


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


def _resolve_unknown_hanging_piece(
    motif: str,
    motif_board: chess.Board,
    user_board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> str | None:
    if motif != "unknown" or not _is_new_hanging_piece(motif_board, user_board, mover_color):
        return None
    has_hanging_attack = any(
        _is_hanging_attack(user_board, mover_color, square, move)
        for square in _iter_opponent_squares(user_board, mover_color)
    )
    return "hanging_piece" if has_hanging_attack else None


def _resolve_checkmate_motif(
    user_board: chess.Board,
    capture_motif: str | None,
) -> str | None:
    if not user_board.is_checkmate():
        return None
    return "hanging_piece" if capture_motif == "hanging_piece" else "mate"


def _resolve_hanging_capture_motif(
    motif: str,
    capture_motif: str | None,
) -> str | None:
    if capture_motif != "hanging_piece":
        return None
    if motif in {"skewer", "discovered_attack", "discovered_check"}:
        return motif
    return "hanging_piece"


def _is_explicit_motif(motif: str) -> bool:
    return motif in {
        "skewer",
        "pin",
        "fork",
        "discovered_attack",
        "discovered_check",
        "mate",
    }


def _resolve_forced_motif(
    motif: str,
    user_board: chess.Board,
    capture_motif: str | None,
) -> str | None:
    checkmate_motif = _resolve_checkmate_motif(user_board, capture_motif)
    if checkmate_motif is not None:
        return checkmate_motif
    return _resolve_hanging_capture_motif(motif, capture_motif)


def _resolve_non_forced_motif(
    context: "NonForcedMotifContext",
) -> str:
    if _is_explicit_motif(context.motif):
        return context.motif
    if not context.allow_new_hanging:
        return context.motif
    return (
        _resolve_unknown_hanging_piece(
            context.motif,
            context.motif_board,
            context.user_board,
            context.move,
            context.mover_color,
        )
        or context.motif
    )


def _is_hanging_attack(
    user_board: chess.Board,
    mover_color: bool,
    square: chess.Square,
    move: chess.Move,
) -> bool:
    if square not in user_board.attacks(move.to_square):
        return False
    if not BaseTacticDetector.has_legal_capture_on_square(
        user_board,
        square,
        mover_color,
    ):
        return False
    return not BaseTacticDetector.has_legal_capture_on_square(
        user_board,
        square,
        not mover_color,
    )


def _iter_opponent_squares(
    board: chess.Board,
    mover_color: bool,
) -> Iterable[chess.Square]:
    for square, piece in board.piece_map().items():
        if piece.color != mover_color:
            yield square


@dataclass(frozen=True)
class NonForcedMotifContext:
    motif: str
    motif_board: chess.Board
    user_board: chess.Board
    move: chess.Move
    mover_color: bool
    allow_new_hanging: bool


@funclogger
def _infer_hanging_or_detected_motif(
    motif_board: chess.Board,
    move: chess.Move,
    mover_color: bool,
    *,
    allow_new_hanging: bool = True,
) -> str:
    user_board = motif_board.copy()
    user_board.push(move)
    motif = MOTIF_DETECTORS.infer_motif(motif_board, move)
    capture_motif = _resolve_capture_motif(motif_board, user_board, move, mover_color)
    forced_motif = _resolve_forced_motif(motif, user_board, capture_motif)
    if forced_motif is not None:
        return forced_motif
    return _resolve_non_forced_motif(
        NonForcedMotifContext(
            motif=motif,
            motif_board=motif_board,
            user_board=user_board,
            move=move,
            mover_color=mover_color,
            allow_new_hanging=allow_new_hanging,
        )
    )
