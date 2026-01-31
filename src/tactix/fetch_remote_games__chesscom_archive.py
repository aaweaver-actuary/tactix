from __future__ import annotations

from tactix.apply_client_method__chesscom_client import _client_method
from tactix.config import Settings
from tactix.define_chesscom_client__chesscom_client import ChesscomClient


def _fetch_remote_games(
    settings: Settings, since_ms: int, *, full_history: bool = False
) -> list[dict]:
    """Fetch Chess.com games from the remote API.

    Args:
        settings: Settings for the request.
        since_ms: Minimum timestamp for included games.
        full_history: Whether to fetch full history.

    Returns:
        Raw game rows.
    """

    return _client_method(
        settings,
        ChesscomClient._fetch_remote_games,
        since_ms,
        full_history,
    )
