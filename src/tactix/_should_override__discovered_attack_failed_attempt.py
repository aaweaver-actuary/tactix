"""Override checks for discovered attack failed attempts."""

from tactix.should_override_failed_attempt__tactics import _should_override_failed_attempt


def _should_override__discovered_attack_failed_attempt(
    result: str,
    swing: int | None,
    threshold: int | None,
    target_motif: str,
) -> bool:
    """Return True if a discovered attack failed attempt should override."""
    return _should_override_failed_attempt(result, swing, threshold, target_motif)
