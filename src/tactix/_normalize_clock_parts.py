from tactix.CLOCK_PARTS_FULL import CLOCK_PARTS_FULL
from tactix.CLOCK_PARTS_SHORT import CLOCK_PARTS_SHORT


def _normalize_clock_parts(token: str) -> tuple[str, str, str] | None:
    parts = token.split(":")
    if len(parts) == CLOCK_PARTS_FULL:
        return parts[0], parts[1], parts[2]
    if len(parts) == CLOCK_PARTS_SHORT:
        return "0", parts[0], parts[1]
    return None
