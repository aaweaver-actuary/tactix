"""Detector for capture motifs."""

from __future__ import annotations

from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.TacticContext import TacticContext


class CaptureDetector(BaseTacticDetector):
    """Detect simple captures when no higher-priority motif applies."""

    motif = "capture"

    def detect(self, context: TacticContext) -> bool:
        """Return True when the move is a capture."""
        return context.board_before.is_capture(context.best_move)
