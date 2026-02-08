"""Fetch Lichess games as part of the pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from tactix.config import Settings
from tactix.FetchContext import FetchContext
from tactix.infra.clients.lichess_client import (
    LichessFetchRequest,
    build_cursor,
    read_checkpoint,
    resolve_fetch_window,
)
from tactix.ports.game_source_client import GameSourceClient


def _resolve_fetch_window(
    settings: Settings,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> tuple[str | None, str | None, int, int | None]:
    cursor_before = read_checkpoint(settings.checkpoint_path)
    use_backfill = backfill_mode and cursor_before is None
    cursor_value, since_ms, until_ms = resolve_fetch_window(
        cursor_before,
        use_backfill,
        window_start_ms,
        window_end_ms,
    )
    return cursor_before, cursor_value, since_ms, until_ms


def _resolve_next_cursor(
    cursor_value: str | None,
    fetch_result: object,
    raw_games: list[Mapping[str, object]],
) -> str | None:
    next_cursor = getattr(fetch_result, "next_cursor", None)
    if not next_cursor and raw_games:
        latest_game = max(
            raw_games,
            key=lambda row: (
                int(row.get("last_timestamp_ms", 0)),
                str(row.get("game_id", "")),
            ),
        )
        next_cursor = build_cursor(
            int(latest_game.get("last_timestamp_ms", 0)),
            str(latest_game.get("game_id", "")),
        )
    return next_cursor or cursor_value


def _fetch_lichess_games(
    settings: Settings,
    client: GameSourceClient,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> FetchContext:
    cursor_before, cursor_value, since_ms, until_ms = _resolve_fetch_window(
        settings,
        backfill_mode,
        window_start_ms,
        window_end_ms,
    )
    fetch_result = client.fetch_incremental_games(
        LichessFetchRequest(
            since_ms=since_ms,
            until_ms=until_ms,
            cursor=cursor_value,
        )
    )
    raw_games = [cast(Mapping[str, object], row) for row in fetch_result.games]
    next_cursor = _resolve_next_cursor(cursor_value, fetch_result, raw_games)
    return FetchContext(
        raw_games=raw_games,
        since_ms=since_ms,
        cursor_before=cursor_before,
        cursor_value=cursor_value,
        next_cursor=next_cursor,
        chesscom_result=None,
        last_timestamp_ms=fetch_result.last_timestamp_ms,
    )
