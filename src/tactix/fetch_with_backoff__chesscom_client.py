"""Fetch Chess.com URLs with backoff handling."""

# pylint: disable=protected-access

from __future__ import annotations

import requests

from tactix.apply_client_method__chesscom_client import _client_method
from tactix.config import Settings
from tactix.define_chesscom_client__chesscom_client import ChesscomClient


def _get_with_backoff(settings: Settings, url: str, timeout: int) -> requests.Response:
    """Fetch a URL with exponential backoff on 429 responses.

    Args:
        settings: Settings for the request.
        url: URL to request.
        timeout: Timeout in seconds.

    Returns:
        Response object.
    """

    return _client_method(settings, ChesscomClient._get_with_backoff, url, timeout)
