"""Utilities for working with timestamps."""

from collections.abc import Iterable, Mapping


def latest_timestamp(rows: Iterable[Mapping[str, object]]) -> int:
    """Return the latest timestamp value from row mappings."""
    ts = 0
    for row in rows:
        value = row.get("last_timestamp_ms", 0)
        if isinstance(value, (int, float, bool)):
            current = int(value)
        elif isinstance(value, str):
            try:
                current = int(value)
            except ValueError:
                current = 0
        else:
            current = 0
        ts = max(ts, current)
    return ts
