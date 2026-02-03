from __future__ import annotations

from datetime import datetime

from tactix.utils import Now


def _resolve_timestamp(value: datetime | None) -> datetime:
    return value if value is not None else Now.as_datetime()
