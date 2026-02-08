from tactix.analyze_tactics__positions import (
    _FAILED_ATTEMPT_OVERRIDE_TARGETS,
    _MISSED_OVERRIDE_TARGETS,
    _OVERRIDEABLE_USER_MOTIFS,
)
from tactix.utils.logger import funclogger


def _is_hanging_override_case(best_motif: str | None, result: str) -> bool:
    return best_motif == "hanging_piece" and result in {"missed", "failed_attempt"}


def _is_hanging_override_allowed(user_motif: str) -> bool:
    return user_motif not in {"skewer", "discovered_attack", "discovered_check"}


def _override_targets_for_result(result: str) -> set[str] | None:
    if result == "missed":
        return _MISSED_OVERRIDE_TARGETS
    if result == "failed_attempt":
        return _FAILED_ATTEMPT_OVERRIDE_TARGETS
    return None


def _best_motif_in_targets(best_motif: str | None, result: str) -> bool:
    targets = _override_targets_for_result(result)
    return bool(targets and best_motif in targets)


def _should_override_standard_motif(
    user_motif: str,
    best_motif: str | None,
    result: str,
) -> bool:
    if user_motif not in _OVERRIDEABLE_USER_MOTIFS:
        return False
    return _best_motif_in_targets(best_motif, result)


@funclogger
def _should_override_motif(user_motif: str, best_motif: str | None, result: str) -> bool:
    if _is_hanging_override_case(best_motif, result):
        return _is_hanging_override_allowed(user_motif)
    return _should_override_standard_motif(user_motif, best_motif, result)
