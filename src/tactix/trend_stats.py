"""API handler for trend stats."""

from typing import Annotated

from fastapi import Depends

from tactix.app.use_cases.dashboard import DashboardUseCase, get_dashboard_use_case
from tactix.dashboard_query_filters import DashboardQueryFilters


def trend_stats(
    filters: Annotated[DashboardQueryFilters, Depends()],
    use_case: Annotated[DashboardUseCase, Depends(get_dashboard_use_case)],
) -> dict[str, object]:
    """Return trend stats payload for the provided filters."""
    return use_case.get_trend_stats(filters)
