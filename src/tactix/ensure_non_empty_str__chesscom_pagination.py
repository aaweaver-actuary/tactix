from __future__ import annotations


def _non_empty_str(value: str) -> str | None:
    return value if value else None
