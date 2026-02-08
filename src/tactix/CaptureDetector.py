"""Detector for capture motifs."""

from __future__ import annotations

from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.TacticContext import TacticContext
from tactix.TacticFinding import TacticFinding


class CaptureDetector(BaseTacticDetector):
    """Detect simple captures when no higher-priority motif applies."""

    motif = "capture"

    def detect(self, context: TacticContext) -> list[TacticFinding]:
        """Return findings when the move is a capture."""
        if context.board_before.is_capture(context.best_move):
            return [TacticFinding(motif=self.motif)]
        return []
