from __future__ import annotations

from tactix.DailySyncStartContext import FetchProgressContext
from tactix.emit_progress__pipeline import _emit_progress


def _emit_fetch_progress(
    ctx: FetchProgressContext,
) -> None:
    _emit_progress(
        ctx.progress,
        "fetch_games",
        source=ctx.settings.source,
        fetched_games=ctx.fetched_games,
        since_ms=ctx.fetch_context.since_ms,
        cursor=ctx.fetch_context.next_cursor or ctx.fetch_context.cursor_value,
        backfill=ctx.backfill_mode,
        backfill_start_ms=ctx.window_start_ms,
        backfill_end_ms=ctx.window_end_ms,
    )
