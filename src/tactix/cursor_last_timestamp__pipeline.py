"""Parse last timestamps from cursor values."""

from __future__ import annotations


def _cursor_last_timestamp(cursor_value: str | None) -> int:
    if not cursor_value:
        return 0
    try:
        return int(cursor_value.split(":", 1)[0])
    except ValueError:
        return 0
