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
    ) -> None:
        super().__init__(context)
        self._games = list(games or [])
        self._next_cursor = next_cursor

    def fetch_incremental_games(self, request: ChessFetchRequest) -> ChessFetchResult:
        games: list[dict[str, object]] = []
        for game in self._games:
            if isinstance(game, ChessGameRow):
                games.append(game.model_dump())
            else:
                games.append(dict(game))
        last_ts = max(
            (cast(int, row.get("last_timestamp_ms", 0)) for row in games), default=0
        )
        return self._build_fetch_result(games, self._next_cursor, last_ts)
