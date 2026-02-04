"""Check whether a missed mate threshold is met."""


def _is_missed_mate(result: str, after_cp: int, threshold: int) -> bool:
    return result == "missed" and after_cp >= threshold
