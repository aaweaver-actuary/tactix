"""Extract clock tokens from PGN comments."""

from tactix.CLK_PATTERN import CLK_PATTERN


def _clock_token(comment: str) -> str | None:
    """Return the clock token from a comment, if any."""
    match = CLK_PATTERN.search(comment or "")
    if not match:
        return None
    return match.group(1)
