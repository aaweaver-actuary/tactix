"""Extract the first non-empty string from pagination payloads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def _first_string(mapping: Mapping[str, object], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value:
            return value
    return None
