"""Emit daily sync start events."""

from __future__ import annotations

from tactix.DailySyncStartContext import DailySyncStartContext
from tactix.emit_progress__pipeline import _emit_progress
from tactix.ops_event import OpsEvent
from tactix.record_ops_event import record_ops_event


def _emit_daily_sync_start(
    ctx: DailySyncStartContext,
) -> None:
    """Emit progress and ops events for a sync start."""
    _emit_progress(
        ctx.progress,
        "start",
        source=ctx.settings.source,
        message="Starting pipeline run",
    )
    record_ops_event(
        OpsEvent(
            settings=ctx.settings,
            component=ctx.settings.run_context,
            event_type="daily_game_sync_start",
            source=ctx.settings.source,
            profile=ctx.profile,
            metadata={
                "backfill": ctx.backfill_mode,
                "window_start_ms": ctx.window_start_ms,
                "window_end_ms": ctx.window_end_ms,
            },
        )
    )
