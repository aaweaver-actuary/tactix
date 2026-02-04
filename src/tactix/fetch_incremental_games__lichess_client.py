"""Fetch incremental Lichess games using shared helpers."""

from __future__ import annotations

from tactix.chess_clients import game_fetching
from tactix.config import Settings


def fetch_incremental_games(
    settings: Settings, since_ms: int, until_ms: int | None = None
) -> list[dict]:
    """Fetch Lichess games incrementally.

    Args:
        settings: Settings for the request.
        since_ms: Minimum timestamp for included games.
        until_ms: Optional upper bound timestamp.

    Returns:
        List of game rows.
    """

    return game_fetching.fetch_incremental_games(settings, since_ms, until_ms)
