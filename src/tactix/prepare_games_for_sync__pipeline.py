"""Prepare games for sync, including filters and expansion."""

from __future__ import annotations

from tactix.DailySyncStartContext import (
    FetchProgressContext,
    PrepareGamesForSyncContext,
    WindowFilterContext,
)
from tactix.emit_fetch_progress__pipeline import _emit_fetch_progress
from tactix.fetch_incremental_games__pipeline import _fetch_incremental_games
from tactix.filter_games_for_window__pipeline import _filter_games_for_window
from tactix.maybe_emit_window_filtered__pipeline import _maybe_emit_window_filtered
from tactix.normalize_and_expand_games__pipeline import _normalize_and_expand_games
from tactix.pipeline_state__pipeline import FetchContext, GameRow
from tactix.resolve_last_timestamp_value__pipeline import _resolve_last_timestamp_value


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
