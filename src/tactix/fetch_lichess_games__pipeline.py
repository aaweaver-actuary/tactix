"""Fetch Lichess games as part of the pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from tactix.config import Settings
from tactix.FetchContext import FetchContext
from tactix.lichess_client import LichessFetchRequest, read_checkpoint
from tactix.pipeline_state__pipeline import ZERO_COUNT
from tactix.ports.game_source_client import GameSourceClient


def _fetch_lichess_games(
    settings: Settings,
    client: GameSourceClient,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> FetchContext:
    checkpoint_before = read_checkpoint(settings.checkpoint_path)
    since_ms = window_start_ms if backfill_mode else checkpoint_before
    if since_ms is None:
        since_ms = ZERO_COUNT
    until_ms = window_end_ms if backfill_mode else None
    raw_games = [
        cast(Mapping[str, object], row)
        for row in client.fetch_incremental_games(
            LichessFetchRequest(since_ms=since_ms, until_ms=until_ms)
        ).games
    ]
    return FetchContext(
        raw_games=raw_games,
        since_ms=since_ms,
        cursor_before=None,
        cursor_value=None,
        next_cursor=None,
        chesscom_result=None,
        last_timestamp_ms=since_ms,
    )
