from __future__ import annotations

from tactix.apply_client_method__chesscom_client import _client_method
from tactix.config import Settings
from tactix.define_chesscom_client__chesscom_client import ChesscomClient


def _load_fixture_games(settings: Settings, since_ms: int) -> list[dict]:
    """Load Chess.com fixture games.

    Args:
        settings: Settings for fixtures.
        since_ms: Minimum timestamp for included games.

    Returns:
        Raw fixture games.
    """

    return _client_method(settings, ChesscomClient._load_fixture_games, since_ms)
