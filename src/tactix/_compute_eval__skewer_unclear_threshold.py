from tactix.analyze_tactics__positions import _SKEWER_UNCLEAR_SWING_THRESHOLD
from tactix.config import Settings


def _compute_eval__skewer_unclear_threshold(settings: Settings | None) -> int | None:
    del settings
    return _SKEWER_UNCLEAR_SWING_THRESHOLD
