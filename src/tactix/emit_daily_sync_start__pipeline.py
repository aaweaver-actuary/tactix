from __future__ import annotations

from tactix.config import Settings
from tactix.emit_progress__pipeline import _emit_progress
from tactix.pipeline_state__pipeline import ProgressCallback
from tactix.record_ops_event import record_ops_event


def _emit_daily_sync_start(
    settings: Settings,
    progress: ProgressCallback | None,
    profile: str | None,
    backfill_mode: bool,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> None:
    _emit_progress(
        progress,
        "start",
        source=settings.source,
        message="Starting pipeline run",
    )
    record_ops_event(
        settings,
        component=settings.run_context,
        event_type="daily_game_sync_start",
        source=settings.source,
        profile=profile,
        metadata={
            "backfill": backfill_mode,
            "window_start_ms": window_start_ms,
            "window_end_ms": window_end_ms,
        },
    )
