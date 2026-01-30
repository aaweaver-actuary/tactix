from __future__ import annotations


def _cache_value(value: str | None, default: str = "all") -> str:
    return value or default
