"""Detector for fork tactics."""

from __future__ import annotations

from tactix._forks_meet_threshold import _forks_meet_threshold
from tactix._is_fork_piece import _is_fork_piece
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.TacticContext import TacticContext
from tactix.TacticFinding import TacticFinding


class ForkDetector(BaseTacticDetector):
    """Detect fork motifs that attack multiple high-value targets."""

    motif = "fork"

    def detect(self, context: TacticContext) -> list[TacticFinding]:
        """Return findings when the move creates a fork."""
        to_square = context.best_move.to_square
        piece = context.board_after.piece_at(to_square)
        if not _is_fork_piece(piece):
            return []
        fork_targets = self.count_high_value_targets(
            context.board_after,
            to_square,
            context.mover_color,
        )
        if _forks_meet_threshold(fork_targets, context.board_after):
            return [TacticFinding(motif=self.motif)]
        return []
