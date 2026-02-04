"""Emit analysis progress updates when appropriate."""

from __future__ import annotations

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import (
    INDEX_OFFSET,
    ZERO_COUNT,
    ProgressCallback,
)
from tactix.emit_progress__pipeline import _emit_progress


def _maybe_emit_analysis_progress(
    progress: ProgressCallback | None,
    settings: Settings,
    idx: int,
    total_positions: int,
    progress_every: int,
) -> None:
    if not progress:
        return
    if idx == total_positions - INDEX_OFFSET or (idx + INDEX_OFFSET) % progress_every == ZERO_COUNT:
        _emit_progress(
            progress,
            "analyze_positions",
            source=settings.source,
            analyzed=idx + INDEX_OFFSET,
            total=total_positions,
        )
