def _should_override__skewer_failed_attempt(
    result: str,
    swing: int | None,
    threshold: int | None,
    target_motif: str,
) -> bool:
    return bool(
        result == "unclear"
        and swing is not None
        and threshold is not None
        and swing <= threshold
        and target_motif
    )
