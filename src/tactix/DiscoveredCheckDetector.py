"""Detector for discovered check motifs."""

from __future__ import annotations

from tactix._has_discovered_check import _has_discovered_check
from tactix._opponent_king_square import _opponent_king_square
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.DiscoveredCheckContext import DiscoveredCheckContext
from tactix.TacticContext import TacticContext
from tactix.TacticFinding import TacticFinding


class DiscoveredCheckDetector(BaseTacticDetector):
    """Detect discovered checks."""

    motif = "discovered_check"

    def detect(self, context: TacticContext) -> list[TacticFinding]:
        """Return findings when a discovered check is present."""
        king_square = _opponent_king_square(context.board_after, context.mover_color)
        if king_square is None:
            return []
        if _has_discovered_check(
            DiscoveredCheckContext(
                detector=self,
                board_before=context.board_before,
                board_after=context.board_after,
                mover_color=context.mover_color,
                king_square=king_square,
                exclude_square=context.best_move.to_square,
            )
        ):
            return [TacticFinding(motif=self.motif)]
        return []
