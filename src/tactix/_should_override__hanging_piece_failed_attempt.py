from tactix.should_override_failed_attempt__tactics import _should_override_failed_attempt


def _should_override__hanging_piece_failed_attempt(
    result: str,
    swing: int | None,
    threshold: int | None,
    target_motif: str,
) -> bool:
    return _should_override_failed_attempt(result, swing, threshold, target_motif)
