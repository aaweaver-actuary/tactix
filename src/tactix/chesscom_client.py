"""Public exports for the Chess.com client."""

# pylint: disable=protected-access

from __future__ import annotations

from tactix.infra.clients import chesscom_client as _client

ARCHIVES_URL = _client.ARCHIVES_URL
ChesscomClient = _client.ChesscomClient
ChesscomClientContext = _client.ChesscomClientContext
_auth_headers = _client._auth_headers
_build_cursor = _client._build_cursor
_fetch_archive_pages = _client._fetch_archive_pages
_fetch_remote_games = _client._fetch_remote_games
_filter_by_cursor = _client._filter_by_cursor
_get_with_backoff = _client._get_with_backoff
_load_fixture_games = _client._load_fixture_games
_next_page_url = _client._next_page_url
_parse_cursor = _client._parse_cursor
_parse_retry_after = _client._parse_retry_after
fetch_incremental_games = _client.fetch_incremental_games
read_cursor = _client.read_cursor
to_int = _client.to_int
write_cursor = _client.write_cursor

CHESSCOM_PUBLIC_EXPORTS = _client.CHESSCOM_PUBLIC_EXPORTS
__all__ = list(CHESSCOM_PUBLIC_EXPORTS)

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
)
