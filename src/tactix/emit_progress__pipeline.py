from __future__ import annotations

import time

from tactix.pipeline_state__pipeline import ProgressCallback


def _emit_progress(progress: ProgressCallback | None, step: str, **fields: object) -> None:
    if progress is None:
        return
    payload: dict[str, object] = {"step": step, "timestamp": time.time()}
    payload.update(fields)
    progress(payload)
