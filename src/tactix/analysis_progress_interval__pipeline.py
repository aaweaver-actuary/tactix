from __future__ import annotations

from tactix.pipeline_state__pipeline import ANALYSIS_PROGRESS_BUCKETS, INDEX_OFFSET


def _analysis_progress_interval(total_positions: int) -> int:
    if total_positions:
        return max(1, total_positions // ANALYSIS_PROGRESS_BUCKETS)
    return INDEX_OFFSET
