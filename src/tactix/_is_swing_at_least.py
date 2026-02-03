def _is_swing_at_least(swing: int | None, threshold: int) -> bool:
    if swing is None:
        return False
    return swing >= threshold
