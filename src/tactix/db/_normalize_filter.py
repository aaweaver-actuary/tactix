"""Normalize dashboard filter inputs."""

from __future__ import annotations


def _normalize_filter(value: str | None) -> str | None:
    """Normalize a filter string or return None when empty."""
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"", "all", "any"}:
        return None
    return normalized
