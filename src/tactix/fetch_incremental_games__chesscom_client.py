"""Incremental fetch helpers for Chess.com games."""

from __future__ import annotations

from tactix.build_client_for_settings__chesscom_client import _client_for_settings
from tactix.chess_clients.base_chess_client import ChessFetchRequest, ChessFetchResult
from tactix.chess_clients.fetch_helpers import run_incremental_fetch
from tactix.config import Settings


def fetch_incremental_games(
    settings: Settings, cursor: str | None, *, full_history: bool = False
) -> ChessFetchResult:
    """Fetch Chess.com games incrementally.

    Args:
        settings: Settings for the request.
        cursor: Cursor token.
        full_history: Whether to fetch full history.

    Returns:
        Chess.com fetch result containing games and cursor metadata.
    """

    request = ChessFetchRequest(cursor=cursor, full_history=full_history)
    return run_incremental_fetch(
        build_client=lambda: _client_for_settings(settings),
        request=request,
    )
