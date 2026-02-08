"""Check if a discovered line reveals a new target."""

from __future__ import annotations

import chess

from tactix.BaseTacticDetector import HIGH_VALUE_PIECES, BaseTacticDetector


def _has_new_target(
    _detector: BaseTacticDetector,
    board_before: chess.Board,
    board_after: chess.Board,
    square: chess.Square,
    opponent: bool,
) -> bool:
    """Return True when a new high-value target appears after the move."""
    non_king_targets = HIGH_VALUE_PIECES - {chess.KING}

    def has_non_king_target(board: chess.Board) -> bool:
        piece = board.piece_at(square)
        if piece is None or piece.color == opponent:
            return False
        for target in board.attacks(square):
            target_piece = board.piece_at(target)
            if (
                target_piece
                and target_piece.color == opponent
                and target_piece.piece_type in non_king_targets
            ):
                return True
        return False

    return has_non_king_target(board_after) and not has_non_king_target(board_before)
