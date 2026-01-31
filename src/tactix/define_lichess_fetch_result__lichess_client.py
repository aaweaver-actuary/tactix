from __future__ import annotations

from pydantic import Field

from tactix.chess_clients.base_chess_client import ChessFetchResult


class LichessFetchResult(ChessFetchResult):
    """Response payload for Lichess incremental fetches."""

    games: list[dict] = Field(default_factory=list)
