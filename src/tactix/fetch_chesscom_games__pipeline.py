"""Fetch Chess.com games and build a fetch context."""

from __future__ import annotations

from tactix.app.use_cases.pipeline_support import _cursor_last_timestamp
from tactix.chess_clients.chesscom_client import read_cursor as read_chesscom_cursor
from tactix.chesscom_raw_games__pipeline import _chesscom_raw_games
from tactix.config import Settings
from tactix.FetchContext import FetchContext
from tactix.ports.game_source_client import GameSourceClient
from tactix.request_chesscom_games__pipeline import _request_chesscom_games


def _fetch_chesscom_games(
    settings: Settings,
    client: GameSourceClient,
    backfill_mode: bool,
) -> FetchContext:
    """Fetch Chess.com games and return a populated fetch context."""
    cursor_before = read_chesscom_cursor(settings.checkpoint_path)
    cursor_value = None if backfill_mode else cursor_before
    last_timestamp_value = _cursor_last_timestamp(cursor_value)
    chesscom_result = _request_chesscom_games(client, cursor_value, backfill_mode)
    raw_games = _chesscom_raw_games(chesscom_result)
    next_cursor = chesscom_result.next_cursor or cursor_value
    last_timestamp_value = chesscom_result.last_timestamp_ms
    return FetchContext(
        raw_games=raw_games,
        since_ms=0,
        cursor_before=cursor_before,
        cursor_value=cursor_value,
        next_cursor=next_cursor,
        chesscom_result=chesscom_result,
        last_timestamp_ms=last_timestamp_value,
    )
