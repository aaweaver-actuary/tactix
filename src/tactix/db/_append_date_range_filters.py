"""Append date range filters for SQL queries."""

from __future__ import annotations

from datetime import date, datetime


def _append_date_range_filters(
    conditions: list[str],
    params: list[object],
    start_date: date | datetime | None,
    end_date: date | datetime | None,
    column: str,
) -> None:
    """Append date range conditions when start/end dates are provided."""
    if start_date is not None:
        conditions.append(f"CAST({column} AS DATE) >= ?")
        params.append(start_date.date() if isinstance(start_date, datetime) else start_date)
    if end_date is not None:
        conditions.append(f"CAST({column} AS DATE) <= ?")
        params.append(end_date.date() if isinstance(end_date, datetime) else end_date)
