from __future__ import annotations

from typing import Mapping, cast

from tactix.base_chess_client import (
    BaseChessClient,
    BaseChessClientContext,
    ChessFetchRequest,
    ChessFetchResult,
    ChessGameRow,
)


class MockChessClient(BaseChessClient):
    """Mock chess client that returns in-memory game rows."""

    def __init__(
        self,
        context: BaseChessClientContext,
        games: list[ChessGameRow | Mapping[str, object]] | None = None,
        next_cursor: str | None = None,
        page_size: int | None = None,
    ) -> None:
        super().__init__(context)
        self._games = list(games or [])
        self._next_cursor = next_cursor
        self._page_size = page_size

    def _normalize_games(self) -> list[dict[str, object]]:
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
        if request.full_history:
            return games
        since_ms = request.since_ms or 0
        until_ms = request.until_ms
        filtered: list[dict[str, object]] = []
        for row in games:
            last_ts = cast(int, row.get("last_timestamp_ms", 0))
            if last_ts < since_ms:
                continue
            if until_ms is not None and last_ts >= until_ms:
                continue
            filtered.append(row)
        return filtered

    def _apply_cursor(
        self,
        games: list[dict[str, object]],
        request: ChessFetchRequest,
    ) -> tuple[list[dict[str, object]], str | None]:
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
        if offset + len(page) < len(games):
            next_cursor = str(offset + len(page))
        else:
            next_cursor = None
        return page, next_cursor

    def fetch_incremental_games(self, request: ChessFetchRequest) -> ChessFetchResult:
        games = self._normalize_games()
        games = self._apply_window(games, request)
        games, next_cursor = self._apply_cursor(games, request)
        last_ts = max(
            (cast(int, row.get("last_timestamp_ms", 0)) for row in games), default=0
        )
        return self._build_fetch_result(games, next_cursor, last_ts)
