"""Helpers for failed attempt overrides."""

from __future__ import annotations

from tactix.domain.tactics_outcome import should_override_failed_attempt


def _should_override_failed_attempt(
    result: str,
    swing: int | None,
    threshold: int | None,
    target_motif: str,
) -> bool:
    """Return True when a failed attempt override should apply."""
    return should_override_failed_attempt(result, swing, threshold, target_motif)
