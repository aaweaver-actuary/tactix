"""Refresh Lichess OAuth tokens."""

from __future__ import annotations

import requests

from tactix.config import Settings
from tactix.define_lichess_token_error__lichess_client import LichessTokenError
from tactix.write_cached_token__lichess_client import _write_cached_token


def _refresh_lichess_token(settings: Settings) -> str:
    """Refresh the OAuth token using the configured refresh token.

    Args:
        settings: Settings for the request.

    Returns:
        Newly refreshed access token.

    Raises:
        LichessTokenError: When refresh configuration or response is invalid.
    """

    refresh_token, client_id, client_secret = (
        settings.lichess.oauth_refresh_token,
        settings.lichess.oauth_client_id,
        settings.lichess.oauth_client_secret,
    )
    token_url = settings.lichess.oauth_token_url
    if not all([refresh_token, client_id, client_secret]):
        raise LichessTokenError("Missing Lichess OAuth refresh token configuration")
    response = requests.post(
        token_url,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    response.raise_for_status()
    access_token = response.json().get("access_token")
    if not access_token:
        raise LichessTokenError("Missing access_token in Lichess OAuth response")
    settings.lichess.token = access_token
    _write_cached_token(settings.lichess_token_cache_path, access_token)
    return access_token
