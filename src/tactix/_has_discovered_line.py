"""Shared helper for discovered line evaluations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import chess

from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.utils.logger import funclogger


@dataclass(frozen=True)
class DiscoveredLineContext:
    """Inputs for detected discovered line analysis."""

    detector: BaseTacticDetector
    board_before: chess.Board
    board_after: chess.Board
    mover_color: bool
    exclude_square: chess.Square


def build_discovered_line_context(source: object) -> DiscoveredLineContext:
    """Build a DiscoveredLineContext from a richer context object."""
    return DiscoveredLineContext(
        source.detector,
        source.board_before,
        source.board_after,
        source.mover_color,
        source.exclude_square,
    )


@funclogger
def _has_discovered_line(
    context: DiscoveredLineContext,
    predicate: Callable[[chess.Square], bool],
) -> bool:
    for square, _piece in context.detector.iter_unchanged_sliders(
        context.board_before,
        context.board_after,
        context.mover_color,
        exclude_square=context.exclude_square,
    ):
        if predicate(square):
            return True
    return False
