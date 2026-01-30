from pydantic import BaseModel, Field


class ChessFetchResult(BaseModel):
    """Response model for incremental fetches.

    Attributes:
        games: Parsed game rows as dictionaries.
        next_cursor: Cursor to resume from on the next request.
        last_timestamp_ms: Latest timestamp seen across all games.

    Example:
        >>> ChessFetchResult(games=[], next_cursor=None, last_timestamp_ms=0)
    """

    games: list[dict] = Field(default_factory=list)
    next_cursor: str | None = None
    last_timestamp_ms: int = 0
