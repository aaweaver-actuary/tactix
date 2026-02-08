"""Context for discovered check detection."""

# pylint: disable=invalid-name

from __future__ import annotations

from dataclasses import dataclass

import chess

from tactix.BaseTacticDetector import BaseTacticDetector


@dataclass(frozen=True)
class DiscoveredCheckContext:
    """Inputs for discovered check evaluation."""

    detector: BaseTacticDetector
    board_before: chess.Board
    board_after: chess.Board
    mover_color: bool
    king_square: chess.Square
    exclude_square: chess.Square | None = None
