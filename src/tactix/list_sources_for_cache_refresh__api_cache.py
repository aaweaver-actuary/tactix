"""Resolve sources to refresh for dashboard cache."""

from __future__ import annotations

from tactix.normalize_source__source import _normalize_source


def _sources_for_cache_refresh(source: str | None) -> list[str | None]:
    """Return normalized sources for cache refresh requests."""
    normalized = _normalize_source(source)
    sources: list[str | None] = [None]
    if normalized is not None:
        sources.append(normalized)
    return sources
