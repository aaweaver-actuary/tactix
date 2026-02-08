"""Detector for pin motifs."""

from __future__ import annotations

import chess

from tactix._is_line_tactic import _is_line_tactic
from tactix._skewer_sources import _skewer_sources
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.LineTacticContext import LineTacticContext
from tactix.TacticContext import TacticContext
from tactix.TacticFinding import TacticFinding


class PinDetector(BaseTacticDetector):
    """Detect pin motifs."""

    motif = "pin"

    def detect(self, context: TacticContext) -> list[TacticFinding]:
        """Return findings when a pin is created."""
        after_pins = self._pin_signatures(context.board_after, context.mover_color)
        if not after_pins:
            return []
        before_pins = self._pin_signatures(context.board_before, context.mover_color)
        if after_pins - before_pins:
            return [TacticFinding(motif=self.motif)]
        return []

    def _pin_signatures(self, board: chess.Board, mover_color: bool) -> set[tuple[int, int]]:
        opponent = not mover_color
        signatures: set[tuple[int, int]] = set()
        for square, steps in _skewer_sources(board, mover_color):
            for step in steps:
                if _is_line_tactic(LineTacticContext(self, board, square, step, opponent, False)):
                    signatures.add((square, step))
        return signatures
