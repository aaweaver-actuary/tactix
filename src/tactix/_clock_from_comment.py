"""Parse clock values from PGN comments."""

from tactix._clock_to_seconds import _clock_to_seconds
from tactix._clock_token import _clock_token
from tactix._normalize_clock_parts import _normalize_clock_parts


def _clock_from_comment(comment: str) -> float | None:
    """Return clock seconds parsed from a comment, if present."""
    token = _clock_token(comment)
    if token is None:
        return None
    clock_parts = _normalize_clock_parts(token)
    if clock_parts is None:
        return None
    return _clock_to_seconds(*clock_parts)
