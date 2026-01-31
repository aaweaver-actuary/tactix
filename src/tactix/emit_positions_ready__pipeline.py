from __future__ import annotations

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import ProgressCallback
from tactix.emit_progress__pipeline import _emit_progress


def _emit_positions_ready(
    settings: Settings,
    progress: ProgressCallback | None,
    positions: list[dict[str, object]],
) -> None:
    _emit_progress(
        progress,
        "positions_ready",
        source=settings.source,
        positions=len(positions),
    )
