"""Append optional SQL filters."""

from __future__ import annotations


def _append_optional_filter(
    conditions: list[str],
    params: list[object],
    clause: str,
    value: object | None,
) -> None:
    """Append clause and parameter when value is present."""
    if value is None:
        return
    conditions.append(clause)
    params.append(value)
