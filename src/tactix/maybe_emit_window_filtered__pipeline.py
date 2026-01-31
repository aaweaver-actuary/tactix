from __future__ import annotations

from tactix.config import Settings
from tactix.emit_backfill_window_filtered__pipeline import _emit_backfill_window_filtered
from tactix.pipeline_state__pipeline import ProgressCallback


def _maybe_emit_window_filtered(
    settings: Settings,
    progress: ProgressCallback | None,
    backfill_mode: bool,
    window_filtered: int,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> None:
    if not backfill_mode or not window_filtered:
        return
    _emit_backfill_window_filtered(
        settings,
        progress,
        window_filtered,
        window_start_ms,
        window_end_ms,
    )
