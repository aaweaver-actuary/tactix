"""Resolve cursors when no games are returned."""

from __future__ import annotations

from tactix.pipeline_state__pipeline import FetchContext


def _no_games_cursor(backfill_mode: bool, fetch_context: FetchContext) -> str | None:
    if backfill_mode:
        return fetch_context.cursor_before
    return fetch_context.next_cursor or fetch_context.cursor_value
