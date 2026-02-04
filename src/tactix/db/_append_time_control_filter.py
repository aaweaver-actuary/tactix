"""Append time control filters for SQL queries."""

from __future__ import annotations


def _append_time_control_filter(
    conditions: list[str],
    params: list[object],
    time_control: str | None,
    column: str,
) -> None:
    """Append a time control filter when provided."""
    if not time_control:
        return
    conditions.append(f"{column} = ?")
    params.append(time_control)
