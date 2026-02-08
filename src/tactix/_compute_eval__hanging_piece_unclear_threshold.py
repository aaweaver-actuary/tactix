"""Compute hanging piece unclear threshold values."""

from tactix.analyze_tactics__positions import _HANGING_PIECE_UNCLEAR_SWING_THRESHOLD
from tactix.config import Settings


def _compute_eval__hanging_piece_unclear_threshold(settings: Settings | None) -> int | None:
    """Return the eval swing threshold for hanging piece unclear results."""
    del settings
    return _HANGING_PIECE_UNCLEAR_SWING_THRESHOLD
