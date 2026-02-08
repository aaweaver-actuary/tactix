"""Port interface for game source clients."""

# pylint: disable=too-few-public-methods

from __future__ import annotations

from typing import Protocol

from tactix.chess_clients.base_chess_client import ChessFetchRequest, ChessFetchResult


class GameSourceClient(Protocol):
    """Stable interface for chess game source clients."""

    def fetch_incremental_games(self, request: ChessFetchRequest) -> ChessFetchResult:
        """Fetch games incrementally for the requested source."""
