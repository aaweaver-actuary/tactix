"""Fetch Chess.com archive pages via the client."""

# pylint: disable=protected-access

from __future__ import annotations

from tactix.apply_client_method__chesscom_client import _client_method
from tactix.config import Settings
from tactix.define_chesscom_client__chesscom_client import ChesscomClient


def _fetch_archive_pages(settings: Settings, archive_url: str) -> list[dict]:
    """Fetch all pages for a given archive URL.

    Args:
        settings: Settings for the request.
        archive_url: Archive endpoint URL.

    Returns:
        List of raw game dictionaries.
    """

    return _client_method(settings, ChesscomClient._fetch_archive_pages, archive_url)
