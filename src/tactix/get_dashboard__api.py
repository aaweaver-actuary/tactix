"""API handler for dashboard payloads."""

from typing import Annotated

from fastapi import Depends, Query

from tactix.app.use_cases.dashboard import DashboardUseCase, get_dashboard_use_case
from tactix.dashboard_query_filters import DashboardQueryFilters


def get_dashboard(
    filters: Annotated[DashboardQueryFilters, Depends()],
    use_case: Annotated[DashboardUseCase, Depends(get_dashboard_use_case)],
    motif: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    """Return dashboard payload for the provided filters."""
    return use_case.get_dashboard(filters, motif)


__all__ = ["get_dashboard"]
