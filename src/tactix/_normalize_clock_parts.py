"""Normalize clock tokens into full time components."""

CLOCK_PARTS_FULL = 3
CLOCK_PARTS_SHORT = 2


def _normalize_clock_parts(token: str) -> tuple[str, str, str] | None:
    parts = token.split(":")
    if len(parts) == CLOCK_PARTS_FULL:
        return parts[0], parts[1], parts[2]
    if len(parts) == CLOCK_PARTS_SHORT:
        return "0", parts[0], parts[1]
    return None
