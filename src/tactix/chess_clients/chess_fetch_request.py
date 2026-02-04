"""Request model for chess fetches."""

from pydantic import BaseModel


class ChessFetchRequest(BaseModel):
    """Request model for incremental fetches.

    Attributes:
        since_ms: Lower bound timestamp (inclusive) in milliseconds.
        until_ms: Optional upper bound timestamp (exclusive) in milliseconds.
        cursor: Optional cursor token for cursor-based APIs.
        full_history: Whether to fetch full history (bypass window limits).

    Example:
        >>> ChessFetchRequest(since_ms=0, cursor=None, full_history=False)
    """

    since_ms: int = 0
    until_ms: int | None = None
    cursor: str | None = None
    full_history: bool = False
