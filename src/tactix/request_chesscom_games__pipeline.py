from __future__ import annotations

from tactix.infra.clients.chesscom_client import ChesscomFetchRequest, ChesscomFetchResult
from tactix.ports.game_source_client import GameSourceClient


def _request_chesscom_games(
    client: GameSourceClient,
    cursor_value: str | None,
    backfill_mode: bool,
    since_ms: int,
) -> ChesscomFetchResult:
    request = ChesscomFetchRequest(
        cursor=cursor_value,
        full_history=backfill_mode,
        since_ms=since_ms,
    )
    return client.fetch_incremental_games(request)
