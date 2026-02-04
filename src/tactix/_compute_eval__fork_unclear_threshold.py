"""Resolve the fork unclear threshold for evaluation swings."""

from tactix.analyze_tactics__positions import _FORK_UNCLEAR_SWING_THRESHOLD
from tactix.config import Settings


def _compute_eval__fork_unclear_threshold(settings: Settings | None) -> int | None:
    """Return the configured fork unclear threshold."""
    del settings
    return _FORK_UNCLEAR_SWING_THRESHOLD
