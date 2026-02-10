from __future__ import annotations

from tactix.config import Settings
from tactix.detect_tactics__motifs import (
    MotifDetectorSuite,
    build_default_motif_detector_suite,
)
from tactix.StockfishEngine import StockfishEngine
from tactix.utils import Logger

logger = Logger(__name__)


MOTIF_DETECTORS: MotifDetectorSuite = build_default_motif_detector_suite()
_FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS = {
    "discovered_attack": -1200,
    "discovered_check": -950,
    "fork": -500,
    "skewer": -700,
}
_PIN_FAILED_ATTEMPT_SWING_THRESHOLD = -50
_SKEWER_FAILED_ATTEMPT_SWING_THRESHOLD = -50
_DISCOVERED_ATTACK_FAILED_ATTEMPT_SWING_THRESHOLD = -50
_DISCOVERED_CHECK_FAILED_ATTEMPT_SWING_THRESHOLD = -50
_HANGING_PIECE_FAILED_ATTEMPT_SWING_THRESHOLD = -50
_PIN_UNCLEAR_SWING_THRESHOLD = -300
_FORK_UNCLEAR_SWING_THRESHOLD = -300
_SKEWER_UNCLEAR_SWING_THRESHOLD = -300
_DISCOVERED_ATTACK_UNCLEAR_SWING_THRESHOLD = -300
_DISCOVERED_CHECK_UNCLEAR_SWING_THRESHOLD = -300
_HANGING_PIECE_UNCLEAR_SWING_THRESHOLD = -300
_MATE_MISSED_SCORE_MULTIPLIER = 200
_SEVERITY_MIN = 1.0
_SEVERITY_MAX = 1.5
_OVERRIDEABLE_USER_MOTIFS = {"capture", "check", "escape"}
_MISSED_OVERRIDE_TARGETS = {
    "mate",
    "fork",
    "pin",
    "skewer",
    "discovered_attack",
    "discovered_check",
    "hanging_piece",
}
_FAILED_ATTEMPT_OVERRIDE_TARGETS = {
    "mate",
    "fork",
    "pin",
    "skewer",
    "discovered_attack",
    "discovered_check",
    "hanging_piece",
}
MATE_IN_ONE = 1
MATE_IN_TWO = 2
_MATE_IN_ONE_UNCLEAR_SCORE_THRESHOLD = _MATE_MISSED_SCORE_MULTIPLIER * MATE_IN_ONE + 50
_MATE_IN_TWO_UNCLEAR_SWING_THRESHOLD = -50


def _compute_eval__swing_threshold(
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


__all__ = [
    "MATE_IN_ONE",
    "MATE_IN_TWO",
    "MOTIF_DETECTORS",
    "StockfishEngine",
    "_compute_eval__swing_threshold",
]
