"""Lichess client shim for chess_clients namespace."""

# pylint: disable=protected-access

from __future__ import annotations

from tactix.infra.clients import lichess_client as _client

LichessClient = _client.LichessClient
LichessClientContext = _client.LichessClientContext
LichessFetchRequest = _client.LichessFetchRequest
LichessFetchResult = _client.LichessFetchResult
LichessGameRow = _client.LichessGameRow
LichessTokenError = _client.LichessTokenError
_coerce_perf_type = _client._coerce_perf_type
_coerce_pgn_text = _client._coerce_pgn_text
_extract_status_code = _client._extract_status_code
_fetch_remote_games = _client._fetch_remote_games
_fetch_remote_games_once = _client._fetch_remote_games_once
_is_auth_error = _client._is_auth_error
_pgn_to_game_row = _client._pgn_to_game_row
_read_cached_token = _client._read_cached_token
_refresh_lichess_token = _client._refresh_lichess_token
_resolve_access_token = _client._resolve_access_token
_resolve_perf_value = _client._resolve_perf_value
_write_cached_token = _client._write_cached_token
build_client = _client.build_client
fetch_incremental_games = _client.fetch_incremental_games
latest_timestamp = _client.latest_timestamp
os = _client.os
read_checkpoint = _client.read_checkpoint
refresh_lichess_token = _client.refresh_lichess_token
requests = _client.requests
write_checkpoint = _client.write_checkpoint

__all__ = [
    "LichessClient",
    "LichessClientContext",
    "LichessFetchRequest",
    "LichessFetchResult",
    "LichessGameRow",
    "LichessTokenError",
    "_coerce_perf_type",
    "_coerce_pgn_text",
    "_extract_status_code",
    "_fetch_remote_games",
    "_fetch_remote_games_once",
    "_is_auth_error",
    "_pgn_to_game_row",
    "_read_cached_token",
    "_refresh_lichess_token",
    "_resolve_access_token",
    "_resolve_perf_value",
    "_write_cached_token",
    "build_client",
    "fetch_incremental_games",
    "latest_timestamp",
    "os",
    "read_checkpoint",
    "refresh_lichess_token",
    "requests",
    "write_checkpoint",
]

_EXPORT_BINDINGS = (
    LichessClient,
    LichessClientContext,
    LichessFetchRequest,
    LichessFetchResult,
    LichessGameRow,
    LichessTokenError,
    _coerce_perf_type,
    _coerce_pgn_text,
    _extract_status_code,
    _fetch_remote_games,
    _fetch_remote_games_once,
    _is_auth_error,
    _pgn_to_game_row,
    _read_cached_token,
    _refresh_lichess_token,
    _resolve_access_token,
    _resolve_perf_value,
    _write_cached_token,
    build_client,
    fetch_incremental_games,
    latest_timestamp,
    os,
    read_checkpoint,
    refresh_lichess_token,
    requests,
    write_checkpoint,
)
