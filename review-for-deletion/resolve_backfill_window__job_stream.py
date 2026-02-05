from __future__ import annotations

import time as time_module

from tactix.resolve_backfill_end_ms__airflow_jobs import _resolve_backfill_end_ms


def _resolve_backfill_window(
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
) -> tuple[int, int | None]:
    triggered_at_ms = int(time_module.time() * 1000)
    effective_end_ms = _resolve_backfill_end_ms(
        backfill_start_ms,
        backfill_end_ms,
        triggered_at_ms,
    )
    return triggered_at_ms, effective_end_ms
