"""Parse Retry-After header values for Chess.com."""

from __future__ import annotations

from tactix.parse_retry_after_date__chesscom_rate_limit import _parse_retry_after_date
from tactix.parse_retry_after_seconds__chesscom_rate_limit import _parse_retry_after_seconds


def _parse_retry_after(value: str | None) -> float | None:
    """Parse Retry-After header values.

    Args:
        value: Retry-After header value.

    Returns:
        Number of seconds to wait, or None.
    """

    if not value:
        return None
    seconds = _parse_retry_after_seconds(value)
    if seconds is not None:
        return seconds
    return _parse_retry_after_date(value)
