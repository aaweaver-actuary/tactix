"""Detector for pin motifs."""

from __future__ import annotations

import chess

from tactix._has_pin_in_steps import _has_pin_in_steps
from tactix._skewer_sources import _skewer_sources
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.TacticContext import TacticContext


class PinDetector(BaseTacticDetector):
    """Detect pin motifs."""

    motif = "pin"

    def detect(self, context: TacticContext) -> bool:
        """Return True when a pin is created."""
        for square, steps in _skewer_sources(context.board_after, context.mover_color):
            if _has_pin_in_steps(
                self,
                context.board_after,
                square,
                steps,
                opponent=not context.mover_color,
            ):
                return True
        return False
