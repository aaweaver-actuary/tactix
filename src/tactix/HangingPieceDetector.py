"""Detector for hanging piece tactics."""

from __future__ import annotations

from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.TacticContext import TacticContext
from tactix.TacticFinding import TacticFinding


class HangingPieceDetector(BaseTacticDetector):
    """Detect captures that win a hanging piece or trade."""

    motif = "hanging_piece"

    def detect(self, context: TacticContext) -> list[TacticFinding]:
        """Return findings when the move captures a hanging piece."""
        if self.is_hanging_capture(
            context.board_before,
            context.board_after,
            context.best_move,
            context.mover_color,
        ):
            return [TacticFinding(motif=self.motif)]
        return []
