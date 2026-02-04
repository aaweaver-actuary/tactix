"""Parse Retry-After header values in seconds."""

from __future__ import annotations


def _parse_retry_after_seconds(value: str) -> float | None:
    """Parse Retry-After as a numeric duration.

    Args:
        value: Retry-After header value.

    Returns:
        Parsed seconds or None.
    """

    try:
        seconds = float(value)
    except ValueError:
        return None
    return max(seconds, 0.0)
