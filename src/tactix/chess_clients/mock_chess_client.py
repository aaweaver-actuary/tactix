"""Mock chess client implementation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from tactix.chess_clients.base_chess_client import (
    BaseChessClient,
    BaseChessClientContext,
    ChessFetchRequest,
    ChessFetchResult,
)
from tactix.chess_clients.chess_game_row import ChessGameRow


class MockChessClient(BaseChessClient):
    """Mock chess client that returns in-memory game rows."""

    def __init__(
        self,
        context: BaseChessClientContext,
        games: list[ChessGameRow | Mapping[str, object]] | None = None,
        next_cursor: str | None = None,
        page_size: int | None = None,
    ) -> None:
        """Initialize the mock client with optional games and paging."""
        super().__init__(context)
        self._games = list(games or [])
        self._next_cursor = next_cursor
        self._page_size = page_size

    def _normalize_games(self) -> list[dict[str, object]]:
        """Normalize stored games into dictionaries."""
        games: list[dict[str, object]] = []
        for game in self._games:
            if isinstance(game, ChessGameRow):
                games.append(game.model_dump())
            else:
                games.append(dict(game))
        return games

    @staticmethod
    def _apply_window(
        games: list[dict[str, object]],
        request: ChessFetchRequest,
    ) -> list[dict[str, object]]:
        """Apply time window filtering to games."""
        if request.full_history:
            return games
        since_ms = request.since_ms or 0
        until_ms = request.until_ms
        return [
            row
            for row in games
            if _row_in_window(cast(int, row.get("last_timestamp_ms", 0)), since_ms, until_ms)
        ]

    def _apply_cursor(
        self,
        games: list[dict[str, object]],
        request: ChessFetchRequest,
    ) -> tuple[list[dict[str, object]], str | None]:
        """Apply cursor pagination to games."""
        offset = 0
        if request.cursor:
            try:
                offset = int(request.cursor)
            except ValueError:
                offset = 0
        remaining = games[offset:]
        next_cursor = self._next_cursor
        if self._page_size is None:
            return remaining, next_cursor
        page = remaining[: self._page_size]
        next_cursor = str(offset + len(page)) if offset + len(page) < len(games) else None
        return page, next_cursor

    def fetch_incremental_games(self, request: ChessFetchRequest) -> ChessFetchResult:
        """Return paged games based on the request."""
        games = self._normalize_games()
        games = self._apply_window(games, request)
        games, next_cursor = self._apply_cursor(games, request)
        last_ts = max((cast(int, row.get("last_timestamp_ms", 0)) for row in games), default=0)
        return self._build_fetch_result(games, next_cursor, last_ts)


def _row_in_window(last_ts: int, since_ms: int, until_ms: int | None) -> bool:
    return last_ts >= since_ms and (until_ms is None or last_ts < until_ms)
