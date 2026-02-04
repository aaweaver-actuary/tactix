"""Context for discovered attack detection."""

# pylint: disable=invalid-name

from __future__ import annotations

from dataclasses import dataclass

import chess

from tactix.BaseTacticDetector import BaseTacticDetector


@dataclass(frozen=True)
class DiscoveredAttackContext:
    """Inputs for discovered attack evaluation."""

    detector: BaseTacticDetector
    board_before: chess.Board
    board_after: chess.Board
    mover_color: bool
    opponent: bool
    exclude_square: chess.Square | None = None
