"""API endpoint for DuckDB raw PGN summaries."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from tactix.app.use_cases.dashboard import DashboardUseCase, get_dashboard_use_case


def raw_pgns_summary(
    use_case: Annotated[DashboardUseCase, Depends(get_dashboard_use_case)],
    source: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    """Return raw PGN summary payload for the given source."""
    return use_case.get_raw_pgns_summary(source)
