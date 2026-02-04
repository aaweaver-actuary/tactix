"""Emit progress when backfill window filtering occurs."""

from __future__ import annotations

from tactix.config import Settings
from tactix.emit_progress__pipeline import _emit_progress
from tactix.pipeline_state__pipeline import ProgressCallback, logger


def _emit_backfill_window_filtered(
    settings: Settings,
    progress: ProgressCallback | None,
    filtered: int,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> None:
    if not filtered:
        return
    logger.info(
        "Filtered %s games outside backfill window for source=%s",
        filtered,
        settings.source,
    )
    _emit_progress(
        progress,
        "backfill_window_filtered",
        source=settings.source,
        filtered=filtered,
        backfill_start_ms=window_start_ms,
        backfill_end_ms=window_end_ms,
    )
