from tactix.analyze_tactics__positions import (
    _DISCOVERED_ATTACK_FAILED_ATTEMPT_SWING_THRESHOLD,
    _DISCOVERED_CHECK_FAILED_ATTEMPT_SWING_THRESHOLD,
    _HANGING_PIECE_FAILED_ATTEMPT_SWING_THRESHOLD,
    _PIN_FAILED_ATTEMPT_SWING_THRESHOLD,
    _SKEWER_FAILED_ATTEMPT_SWING_THRESHOLD,
)
from tactix.config import Settings
from tactix.utils.logger import funclogger


@funclogger
def _compute_eval__failed_attempt_threshold(
    motif: str,
    settings: Settings | None,
) -> int | None:
    del settings
    thresholds = {
        "pin": _PIN_FAILED_ATTEMPT_SWING_THRESHOLD,
        "skewer": _SKEWER_FAILED_ATTEMPT_SWING_THRESHOLD,
        "discovered_attack": _DISCOVERED_ATTACK_FAILED_ATTEMPT_SWING_THRESHOLD,
        "discovered_check": _DISCOVERED_CHECK_FAILED_ATTEMPT_SWING_THRESHOLD,
        "hanging_piece": _HANGING_PIECE_FAILED_ATTEMPT_SWING_THRESHOLD,
    }
    return thresholds.get(motif)
