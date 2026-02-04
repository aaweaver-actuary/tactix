"""Helpers for determining backfill mode."""

from __future__ import annotations


def _is_backfill_mode(window_start_ms: int | None, window_end_ms: int | None) -> bool:
    """Return True when a backfill window is provided."""
    return window_start_ms is not None or window_end_ms is not None
