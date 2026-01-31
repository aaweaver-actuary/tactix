from __future__ import annotations

from tactix.chess_clients.base_chess_client import BaseChessClient
from tactix.chess_clients.chesscom_client import ChesscomFetchRequest, ChesscomFetchResult


def _request_chesscom_games(
    client: BaseChessClient, cursor_value: str | None, backfill_mode: bool
) -> ChesscomFetchResult:
    return client.fetch_incremental_games(
        ChesscomFetchRequest(cursor=cursor_value, full_history=backfill_mode)
    )
