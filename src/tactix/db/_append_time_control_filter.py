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
    normalized = str(time_control).lower()
    base_expr = f"try_cast(split_part({column}, '+', 1) as INTEGER)"
    ranges: dict[str, tuple[int | None, int | None]] = {
        "bullet": (None, 180),
        "blitz": (180, 600),
        "rapid": (600, 1800),
        "classical": (1800, 7200),
        "correspondence": (7200, None),
    }

    if normalized in ranges:
        lower, upper = ranges[normalized]
        clauses: list[str] = []
        if lower is not None:
            clauses.append(f"{base_expr} > {lower}")
        if upper is not None:
            clauses.append(f"{base_expr} <= {upper}")
        range_expr = " AND ".join(clauses)
        conditions.append(f"({column} = ? OR ({range_expr}))")
        params.append(normalized)
    else:
        conditions.append(f"{column} = ?")
        params.append(time_control)
