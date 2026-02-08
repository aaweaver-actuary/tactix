from tactix.analyze_tactics__positions import _DISCOVERED_ATTACK_UNCLEAR_SWING_THRESHOLD
from tactix.config import Settings


def _compute_eval__discovered_attack_unclear_threshold(settings: Settings | None) -> int | None:
    del settings
    return _DISCOVERED_ATTACK_UNCLEAR_SWING_THRESHOLD
