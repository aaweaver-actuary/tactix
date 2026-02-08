"""Fetch Lichess games as part of the pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import ZERO_COUNT
from tactix.FetchContext import FetchContext
from tactix.infra.clients.lichess_client import (
    LichessFetchRequest,
    _parse_cursor,
    read_checkpoint,
)
from tactix.ports.game_source_client import GameSourceClient


def _fetch_lichess_games(
    settings: Settings,
    client: GameSourceClient,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> FetchContext:
    cursor_before = read_checkpoint(settings.checkpoint_path)
    cursor_value = None if backfill_mode else cursor_before
    since_ms = window_start_ms if backfill_mode else _parse_cursor(cursor_value)[0]
    if since_ms is None:
        since_ms = ZERO_COUNT
    until_ms = window_end_ms if backfill_mode else None
    fetch_result = client.fetch_incremental_games(
        LichessFetchRequest(
            since_ms=since_ms,
            until_ms=until_ms,
            cursor=cursor_value,
        )
    )
    raw_games = [cast(Mapping[str, object], row) for row in fetch_result.games]
    next_cursor = fetch_result.next_cursor or cursor_value
    return FetchContext(
        raw_games=raw_games,
        since_ms=since_ms,
        cursor_before=cursor_before,
        cursor_value=cursor_value,
        next_cursor=next_cursor,
        chesscom_result=None,
        last_timestamp_ms=fetch_result.last_timestamp_ms,
    )
