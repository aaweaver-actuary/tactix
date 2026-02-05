"""Prepare games for sync, including filters and expansion."""

from __future__ import annotations

from tactix.app.use_cases.pipeline_support import (
    _emit_fetch_progress,
    _maybe_emit_window_filtered,
    _resolve_last_timestamp_value,
)
from tactix.fetch_incremental_games__pipeline import _fetch_incremental_games
from tactix.FetchContext import FetchContext
from tactix.filter_games_for_window__pipeline import _filter_games_for_window
from tactix.GameRow import GameRow
from tactix.normalize_and_expand_games__pipeline import _normalize_and_expand_games
from tactix.sync_contexts import (
    FetchProgressContext,
    PrepareGamesForSyncContext,
    WindowFilterContext,
)


def _prepare_games_for_sync(
    context: PrepareGamesForSyncContext,
) -> tuple[list[GameRow], FetchContext, int, int]:
    fetch_context = _fetch_incremental_games(
        context.settings,
        context.client,
        context.backfill_mode,
        context.window_start_ms,
        context.window_end_ms,
    )
    games = _normalize_and_expand_games(fetch_context.raw_games, context.settings)
    games, window_filtered = _filter_games_for_window(
        games,
        context.window_start_ms,
        context.window_end_ms,
    )
    _maybe_emit_window_filtered(
        WindowFilterContext(
            settings=context.settings,
            progress=context.progress,
            backfill_mode=context.backfill_mode,
            window_filtered=window_filtered,
            window_start_ms=context.window_start_ms,
            window_end_ms=context.window_end_ms,
        )
    )
    last_timestamp_value = _resolve_last_timestamp_value(games, fetch_context.last_timestamp_ms)
    _emit_fetch_progress(
        FetchProgressContext(
            settings=context.settings,
            progress=context.progress,
            fetch_context=fetch_context,
            backfill_mode=context.backfill_mode,
            window_start_ms=context.window_start_ms,
            window_end_ms=context.window_end_ms,
            fetched_games=len(games),
        )
    )
    return games, fetch_context, window_filtered, last_timestamp_value
