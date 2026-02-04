"""Fetch incremental games for the pipeline."""

from __future__ import annotations

from tactix.config import Settings
from tactix.fetch_chesscom_games__pipeline import _fetch_chesscom_games
from tactix.fetch_lichess_games__pipeline import _fetch_lichess_games
from tactix.FetchContext import FetchContext
from tactix.ports.game_source_client import GameSourceClient


def _fetch_incremental_games(
    settings: Settings,
    client: GameSourceClient,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> FetchContext:
    """Fetch incremental games for the configured source."""
    if settings.source == "chesscom":
        return _fetch_chesscom_games(settings, client, backfill_mode)
    return _fetch_lichess_games(
        settings,
        client,
        backfill_mode,
        window_start_ms,
        window_end_ms,
    )
