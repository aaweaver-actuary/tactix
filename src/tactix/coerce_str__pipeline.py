"""Coerce values into strings for pipeline inputs."""

from __future__ import annotations


def _coerce_str(value: object) -> str:
    """Return a string representation of the value."""
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)
