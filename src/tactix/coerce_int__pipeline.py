"""Coerce values into integers for pipeline inputs."""

from __future__ import annotations


def _coerce_int(value: object) -> int:
    """Return an integer representation of the value."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0
