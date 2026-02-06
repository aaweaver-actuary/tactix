"""Detector for skewer motifs."""

from __future__ import annotations

from tactix._has_skewer_in_steps import _has_skewer_in_steps
from tactix._skewer_sources import _skewer_sources
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.TacticContext import TacticContext
from tactix.TacticFinding import TacticFinding


class SkewerDetector(BaseTacticDetector):
    """Detect skewer motifs."""

    motif = "skewer"

    def detect(self, context: TacticContext) -> list[TacticFinding]:
        """Return findings when a skewer is created."""
        for square, steps in _skewer_sources(context.board_after, context.mover_color):
            if _has_skewer_in_steps(
                self,
                context.board_after,
                square,
                steps,
                opponent=not context.mover_color,
            ):
                return [TacticFinding(motif=self.motif)]
        return []
