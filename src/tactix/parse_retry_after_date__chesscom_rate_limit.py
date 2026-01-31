from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime


def _parse_retry_after_date(value: str) -> float | None:
    """Parse Retry-After as an HTTP date.

    Args:
        value: Retry-After header value.

    Returns:
        Parsed seconds or None.
    """

    try:
        dt = parsedate_to_datetime(value)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = (dt - datetime.now(UTC)).total_seconds()
    return max(delta, 0.0)
