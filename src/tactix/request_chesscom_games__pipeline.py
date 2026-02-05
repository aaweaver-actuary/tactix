from __future__ import annotations

from tactix.chess_clients.chesscom_client import ChesscomFetchRequest, ChesscomFetchResult
from tactix.ports.game_source_client import GameSourceClient


def _request_chesscom_games(
    client: GameSourceClient, cursor_value: str | None, backfill_mode: bool
) -> ChesscomFetchResult:
    return client.fetch_incremental_games(
        ChesscomFetchRequest(cursor=cursor_value, full_history=backfill_mode)
    )
