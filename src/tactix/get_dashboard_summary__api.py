"""API handler for dashboard summary totals."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from tactix.app.use_cases.dashboard import DashboardUseCase, get_dashboard_use_case
from tactix.dashboard_query_filters import DashboardQueryFilters


def dashboard_summary(  # pragma: no cover
    filters: Annotated[DashboardQueryFilters, Depends()],
    use_case: Annotated[DashboardUseCase, Depends(get_dashboard_use_case)],
    db_name: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    """Return dashboard summary totals for the provided filters."""
    return use_case.get_summary(filters, db_name)


__all__ = ["dashboard_summary"]
