from __future__ import annotations

from fastapi import HTTPException


def _validate_backfill_window(
    backfill_start_ms: int | None,
    backfill_end_ms: int | None,
) -> None:
    if backfill_start_ms is None or backfill_end_ms is None:
        return
    if backfill_start_ms >= backfill_end_ms:
        raise HTTPException(
            status_code=400,
            detail="Backfill window must end after start",
        )
