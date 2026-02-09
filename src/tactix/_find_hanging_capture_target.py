"""Find a hanging capture target for the mover."""

from __future__ import annotations

from dataclasses import dataclass

import chess

from tactix.BaseTacticDetector import BaseTacticDetector


@dataclass(frozen=True)
class HangingCaptureTarget:
    """Describe a hanging capture target."""

    move: chess.Move
    target_piece: str
    target_square: str


def _find_hanging_capture_target(
    board: chess.Board,
    mover_color: bool,
) -> HangingCaptureTarget | None:
    """Return the highest-value hanging capture target, if any."""
    scored_targets = (
        (_score_hanging_target(board, move, target), target)
        for move in sorted(board.legal_moves, key=lambda candidate: candidate.uci())
        if (target := _hanging_target_for_move(board, move, mover_color)) is not None
    )
    _best_score, best_target = max(scored_targets, default=((0, 0, ""), None))
    return best_target


def _hanging_target_for_move(
    board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> HangingCaptureTarget | None:
    if not board.is_capture(move):
        return None
    board_after = board.copy()
    board_after.push(move)
    if not BaseTacticDetector.is_hanging_capture(board, board_after, move, mover_color):
        return None
    capture_square = _capture_square_for_move(board, move, mover_color)
    captured_piece = board.piece_at(capture_square)
    if captured_piece is None:
        return None
    return HangingCaptureTarget(
        move=move,
        target_piece=_piece_label(captured_piece),
        target_square=chess.square_name(capture_square),
    )


def _score_hanging_target(
    board: chess.Board,
    move: chess.Move,
    target: HangingCaptureTarget,
) -> tuple[int, int, str]:
    capture_square = chess.parse_square(target.target_square)
    captured_piece = board.piece_at(capture_square)
    captured_value = (
        BaseTacticDetector.piece_value(captured_piece.piece_type)
        if captured_piece is not None
        else 0
    )
    mover_piece = board.piece_at(move.from_square)
    mover_value = BaseTacticDetector.piece_value(mover_piece.piece_type) if mover_piece else 0
    return (captured_value, -mover_value, move.uci())


def _capture_square_for_move(
    board: chess.Board,
    move: chess.Move,
    mover_color: bool,
) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if mover_color == chess.WHITE else 8)
    return move.to_square


def _piece_label(piece: chess.Piece) -> str:
    labels = {
        chess.PAWN: "pawn",
        chess.KNIGHT: "knight",
        chess.BISHOP: "bishop",
        chess.ROOK: "rook",
        chess.QUEEN: "queen",
        chess.KING: "king",
    }
    return labels.get(piece.piece_type, "unknown")
