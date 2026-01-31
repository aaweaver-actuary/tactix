from __future__ import annotations

from tactix.config import Settings
from tactix.emit_progress__pipeline import _emit_progress
from tactix.pipeline_state__pipeline import FetchContext, ProgressCallback


def _emit_fetch_progress(
    settings: Settings,
    progress: ProgressCallback | None,
    fetch_context: FetchContext,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
    fetched_games: int,
) -> None:
    _emit_progress(
        progress,
        "fetch_games",
        source=settings.source,
        fetched_games=fetched_games,
        since_ms=fetch_context.since_ms,
        cursor=fetch_context.next_cursor or fetch_context.cursor_value,
        backfill=backfill_mode,
        backfill_start_ms=window_start_ms,
        backfill_end_ms=window_end_ms,
    )
