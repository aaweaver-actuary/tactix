"""API helpers for motif statistics."""

from typing import Annotated

from fastapi import Depends

from tactix.app.use_cases.dashboard import DashboardUseCase, get_dashboard_use_case
from tactix.dashboard_query_filters import DashboardQueryFilters


def motif_stats(
    filters: Annotated[DashboardQueryFilters, Depends()],
    use_case: Annotated[DashboardUseCase, Depends(get_dashboard_use_case)],
) -> dict[str, object]:
    """Return motif statistics payload for the dashboard."""
    return use_case.get_motif_stats(filters)
