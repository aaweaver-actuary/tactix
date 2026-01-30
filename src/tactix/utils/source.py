from __future__ import annotations


def normalized_source(value: str | None) -> str:
    return (value or "").strip().lower()
