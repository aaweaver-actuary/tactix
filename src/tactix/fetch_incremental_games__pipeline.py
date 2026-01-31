from __future__ import annotations

from tactix.chess_clients.base_chess_client import BaseChessClient
from tactix.config import Settings
from tactix.fetch_chesscom_games__pipeline import _fetch_chesscom_games
from tactix.fetch_lichess_games__pipeline import _fetch_lichess_games
from tactix.pipeline_state__pipeline import FetchContext


def _fetch_incremental_games(
    settings: Settings,
    client: BaseChessClient,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> FetchContext:
    if settings.source == "chesscom":
        return _fetch_chesscom_games(settings, client, backfill_mode)
    return _fetch_lichess_games(
        settings,
        client,
        backfill_mode,
        window_start_ms,
        window_end_ms,
    )
