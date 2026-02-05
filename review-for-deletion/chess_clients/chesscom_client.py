"""Chess.com client shim for chess_clients namespace."""

# pylint: disable=protected-access

from __future__ import annotations

from tactix.chess_clients.base_chess_client import (
    ChessFetchRequest as ChesscomFetchRequest,
)
from tactix.chess_clients.base_chess_client import (
    ChessFetchResult as ChesscomFetchResult,
)
from tactix.errors import RateLimitError
from tactix.infra.clients import chesscom_client as _legacy

CHESSCOM_PUBLIC_EXPORTS = _legacy.CHESSCOM_PUBLIC_EXPORTS

ARCHIVES_URL = _legacy.ARCHIVES_URL
ChesscomClient = _legacy.ChesscomClient
ChesscomClientContext = _legacy.ChesscomClientContext
_auth_headers = _legacy._auth_headers
_build_cursor = _legacy._build_cursor
_fetch_archive_pages = _legacy._fetch_archive_pages
_fetch_remote_games = _legacy._fetch_remote_games
_filter_by_cursor = _legacy._filter_by_cursor
_get_with_backoff = _legacy._get_with_backoff
_load_fixture_games = _legacy._load_fixture_games
_next_page_url = _legacy._next_page_url
_parse_cursor = _legacy._parse_cursor
_parse_retry_after = _legacy._parse_retry_after
fetch_incremental_games = _legacy.fetch_incremental_games
read_cursor = _legacy.read_cursor
to_int = _legacy.to_int
write_cursor = _legacy.write_cursor

ChesscomRateLimitError = getattr(_legacy, "ChesscomRateLimitError", RateLimitError)

__all__ = list(CHESSCOM_PUBLIC_EXPORTS)
__all__ += [
    "ChesscomFetchRequest",
    "ChesscomFetchResult",
    "ChesscomRateLimitError",
]

_EXPORT_BINDINGS = (
    ARCHIVES_URL,
    ChesscomClient,
    ChesscomClientContext,
    _auth_headers,
    _build_cursor,
    _fetch_archive_pages,
    _fetch_remote_games,
    _filter_by_cursor,
    _get_with_backoff,
    _load_fixture_games,
    _next_page_url,
    _parse_cursor,
    _parse_retry_after,
    fetch_incremental_games,
    read_cursor,
    to_int,
    write_cursor,
    ChesscomFetchRequest,
    ChesscomFetchResult,
    ChesscomRateLimitError,
)
