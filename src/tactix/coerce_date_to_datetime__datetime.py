from __future__ import annotations

from datetime import date, datetime, time


def _coerce_date_to_datetime(value: date | None, *, end_of_day: bool = False) -> datetime | None:
    if value is None:
        return None
    if end_of_day:
        return datetime.combine(value, time.max)
    return datetime.combine(value, time.min)
