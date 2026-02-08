"""Reclassify motif names based on settings rules."""

from tactix.analyze_tactics__positions import _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS
from tactix.utils.logger import funclogger


@funclogger
def _reclassify_motif(motif: str, user_motif: str) -> str | None:
    if user_motif in _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS:
        return user_motif
    if motif in _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS and motif != "discovered_attack":
        return motif
    return None
