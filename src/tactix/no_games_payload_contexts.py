"""Helpers for constructing no-games payload contexts."""

from __future__ import annotations

from tactix.DailySyncStartContext import NoGamesAfterDedupeContext, NoGamesContext
from tactix.sync_contexts import (
    NoGamesAfterDedupePayloadContext,
    NoGamesPayloadContext,
)
from tactix.utils.logger import funclogger


@funclogger
def build_no_games_payload_context(context: NoGamesContext) -> NoGamesPayloadContext:
    """Create a NoGamesPayloadContext from a NoGamesContext."""
    return NoGamesPayloadContext(
        settings=context.settings,
        conn=context.conn,
        backfill_mode=context.backfill_mode,
        window=context.window,
    )


@funclogger
def build_no_games_after_dedupe_payload_context(
    context: NoGamesAfterDedupeContext,
) -> NoGamesAfterDedupePayloadContext:
    """Create a NoGamesAfterDedupePayloadContext from a NoGamesAfterDedupeContext."""
    return NoGamesAfterDedupePayloadContext(
        settings=context.settings,
        conn=context.conn,
        backfill_mode=context.backfill_mode,
        games=context.games,
        window=context.window,
    )
