"""Resolve Lichess access tokens for API calls."""

from __future__ import annotations

from tactix.config import Settings
from tactix.read_cached_token__lichess_client import _read_cached_token


def _resolve_access_token(settings: Settings) -> str:
    """Resolve the active access token.

    Args:
        settings: Settings for the request.

    Returns:
        Access token string (empty if missing).
    """

    if settings.lichess.token:
        return settings.lichess.token
    cached = _read_cached_token(settings.lichess_token_cache_path)
    return cached or ""
