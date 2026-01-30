from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from ..config import Settings
from . import ChessFetchRequest, ChessFetchResult, ChessGameRow


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

        return datetime.now(UTC)

    def _build_game_row(self, game_id: str, pgn: str, last_timestamp_ms: int) -> ChessGameRow:
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
