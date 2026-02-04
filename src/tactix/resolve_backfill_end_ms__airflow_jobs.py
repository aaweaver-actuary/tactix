"""Resolve the backfill end timestamp for Airflow jobs."""

from __future__ import annotations

from tactix.coerce_backfill_end_ms__airflow_jobs import _coerce_backfill_end_ms
from tactix.validate_backfill_window__airflow_jobs import _validate_backfill_window


def _resolve_backfill_end_ms(
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
    triggered_at_ms: int,
) -> int | None:
    if backfill_start_ms is None and backfill_end_ms is None:
        return backfill_end_ms
    effective_end_ms = _coerce_backfill_end_ms(backfill_end_ms, triggered_at_ms)
    _validate_backfill_window(backfill_start_ms, effective_end_ms)
    return effective_end_ms
