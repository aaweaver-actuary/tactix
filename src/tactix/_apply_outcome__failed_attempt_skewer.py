from tactix._select_motif__skewer_target import _select_motif__skewer_target
from tactix._should_override__skewer_failed_attempt import _should_override__skewer_failed_attempt


def _apply_outcome__failed_attempt_skewer(
    result: str,
    motif: str,
    best_motif: str | None,
    swing: int | None,
    threshold: int | None,
) -> tuple[str, str]:
    target_motif = _select_motif__skewer_target(motif, best_motif)
    if _should_override__skewer_failed_attempt(result, swing, threshold, target_motif):
        return "failed_attempt", target_motif
    return result, motif
