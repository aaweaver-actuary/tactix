from __future__ import annotations

from tactix import chesscom_client as _legacy
from tactix.chess_clients.base_chess_client import (
    ChessFetchRequest as ChesscomFetchRequest,
)
from tactix.chess_clients.base_chess_client import (
    ChessFetchResult as ChesscomFetchResult,
)
from tactix.chesscom_client import (
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
from tactix.errors import RateLimitError

try:
    ChesscomRateLimitError = _legacy.ChesscomRateLimitError
except AttributeError:  # pragma: no cover - legacy alias fallback
    ChesscomRateLimitError = RateLimitError

__all__ = [
    "ARCHIVES_URL",
    "ChesscomClient",
    "ChesscomClientContext",
    "ChesscomFetchRequest",
    "ChesscomFetchResult",
    "ChesscomRateLimitError",
    "_auth_headers",
    "_build_cursor",
    "_fetch_archive_pages",
    "_fetch_remote_games",
    "_filter_by_cursor",
    "_get_with_backoff",
    "_load_fixture_games",
    "_next_page_url",
    "_parse_cursor",
    "_parse_retry_after",
    "fetch_incremental_games",
    "read_cursor",
    "to_int",
    "write_cursor",
]
