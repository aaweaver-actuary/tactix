from tactix.analyze_tactics__positions import (
    _FAILED_ATTEMPT_OVERRIDE_TARGETS,
    _MISSED_OVERRIDE_TARGETS,
    _OVERRIDEABLE_USER_MOTIFS,
)
from tactix.utils.logger import funclogger


@funclogger
def _should_override_motif(user_motif: str, best_motif: str | None, result: str) -> bool:
    if best_motif == "hanging_piece" and result in {"missed", "failed_attempt"}:
        return user_motif not in {"skewer", "discovered_attack", "discovered_check"}
    if user_motif not in _OVERRIDEABLE_USER_MOTIFS:
        return False
    if result == "missed":
        return bool(best_motif in _MISSED_OVERRIDE_TARGETS)
    if result == "failed_attempt":
        return bool(best_motif in _FAILED_ATTEMPT_OVERRIDE_TARGETS)
    return False
