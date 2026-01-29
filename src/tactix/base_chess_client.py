from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from pydantic import BaseModel, Field

from tactix.config import Settings


class ChessGameRow(BaseModel):
    """Represents a normalized chess game row.

    Attributes:
        game_id: Stable identifier for the game.
        user: Username associated with the game.
        source: Data source (e.g., "lichess" or "chesscom").
        fetched_at: Timestamp when the game was fetched.
        pgn: Raw PGN text.
        last_timestamp_ms: Last move timestamp in milliseconds.
    """

    game_id: str
    user: str
    source: str
    fetched_at: datetime
    pgn: str
    last_timestamp_ms: int


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


@dataclass(slots=True)
class BaseChessClientContext:
    """Shared context for chess API clients.

    Attributes:
        settings: Application settings used for API calls.
        logger: Logger for client-specific messages.
    """

    settings: Settings
    logger: logging.Logger


class BaseChessClient:
    """Base class for chess API clients.

    Subclasses are expected to implement `fetch_incremental_games`.
    """

    def __init__(self, context: BaseChessClientContext) -> None:
        """Initialize the client with shared context.

        Args:
            context: Base context containing settings and logger.
        """

        self._context = context

    @property
    def settings(self) -> Settings:
        """Expose the settings from the context.

        Returns:
            The active `Settings` instance.
        """

        return self._context.settings

    @property
    def logger(self) -> logging.Logger:
        """Expose the logger from the context.

        Returns:
            Logger used by the client.
        """

        return self._context.logger

    def fetch_incremental_games(self, request: ChessFetchRequest) -> ChessFetchResult:
        """Fetch games incrementally.

        Args:
            request: Request parameters for the incremental fetch.

        Returns:
            A `ChessFetchResult` containing the games and cursor metadata.

        Raises:
            NotImplementedError: When the subclass does not implement this method.

        Example:
            >>> client.fetch_incremental_games(ChessFetchRequest(since_ms=0))
        """

        raise NotImplementedError("Subclasses must implement fetch_incremental_games")

    def _now_utc(self) -> datetime:
        """Return the current UTC time.

        Returns:
            Current UTC datetime.
        """

        return datetime.now(timezone.utc)

    def _build_game_row(
        self, game_id: str, pgn: str, last_timestamp_ms: int
    ) -> ChessGameRow:
        """Create a normalized game row for the active settings.

        Args:
            game_id: Stable identifier for the game.
            pgn: Raw PGN text.
            last_timestamp_ms: Last move timestamp in milliseconds.

        Returns:
            Normalized `ChessGameRow` instance.
        """

        return ChessGameRow(
            game_id=game_id,
            user=self.settings.user,
            source=self.settings.source,
            fetched_at=self._now_utc(),
            pgn=pgn,
            last_timestamp_ms=last_timestamp_ms,
        )

    def _build_fetch_result(
        self,
        games: list[dict],
        next_cursor: str | None,
        last_timestamp_ms: int,
    ) -> ChessFetchResult:
        """Build a fetch result model from raw values.

        Args:
            games: List of normalized game rows.
            next_cursor: Cursor token for the next fetch.
            last_timestamp_ms: Latest timestamp across all games.

        Returns:
            A `ChessFetchResult` instance.
        """

        return ChessFetchResult(
            games=games,
            next_cursor=next_cursor,
            last_timestamp_ms=last_timestamp_ms,
        )
