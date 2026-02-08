"""Normalize source values for API inputs."""

from __future__ import annotations


def _normalize_source(source: str | None) -> str | None:
    """Return a normalized source string or None for all."""
    if source is None:
        return None
    trimmed = source.strip().lower()
    return None if trimmed == "all" else trimmed
