"""Helpers for failed attempt overrides."""

from __future__ import annotations


def _should_override_failed_attempt(
    result: str,
    swing: int | None,
    threshold: int | None,
    target_motif: str,
) -> bool:
    """Return True when a failed attempt override should apply."""
    return bool(
        result == "unclear"
        and swing is not None
        and threshold is not None
        and swing < threshold
        and target_motif
    )
