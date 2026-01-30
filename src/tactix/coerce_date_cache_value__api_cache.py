from __future__ import annotations

from datetime import datetime


def _date_cache_value(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
