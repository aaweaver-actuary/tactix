from __future__ import annotations


def _coerce_backfill_end_ms(backfill_end_ms: int | None, triggered_at_ms: int) -> int | None:
    if backfill_end_ms is None or backfill_end_ms > triggered_at_ms:
        return triggered_at_ms
    return backfill_end_ms
