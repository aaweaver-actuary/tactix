"""Detector for discovered attack motifs."""

from __future__ import annotations

from tactix._has_discovered_attack import _has_discovered_attack
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.DiscoveredAttackContext import DiscoveredAttackContext
from tactix.TacticContext import TacticContext
from tactix.TacticFinding import TacticFinding


class DiscoveredAttackDetector(BaseTacticDetector):
    """Detect discovered attack motifs."""

    motif = "discovered_attack"

    def detect(self, context: TacticContext) -> list[TacticFinding]:
        """Return findings when a discovered attack is present."""
        if _has_discovered_attack(
            DiscoveredAttackContext(
                detector=self,
                board_before=context.board_before,
                board_after=context.board_after,
                mover_color=context.mover_color,
                opponent=not context.mover_color,
                exclude_square=context.best_move.to_square,
            )
        ):
            return [TacticFinding(motif=self.motif)]
        return []
