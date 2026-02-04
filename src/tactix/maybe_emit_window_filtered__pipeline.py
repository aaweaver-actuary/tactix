"""Emit backfill window filter metrics when needed."""

from __future__ import annotations

from tactix.DailySyncStartContext import WindowFilterContext
from tactix.emit_backfill_window_filtered__pipeline import _emit_backfill_window_filtered


def _maybe_emit_window_filtered(
    context: WindowFilterContext,
) -> None:
    if not context.backfill_mode or not context.window_filtered:
        return
    _emit_backfill_window_filtered(
        context.settings,
        context.progress,
        context.window_filtered,
        context.window_start_ms,
        context.window_end_ms,
    )
