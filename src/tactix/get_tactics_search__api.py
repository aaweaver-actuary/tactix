"""API handler for tactics search."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from tactix.app.use_cases.tactics_search import (
    TacticsSearchUseCase,
    get_tactics_search_use_case,
)
from tactix.tactics_search_filters import TacticsSearchFilters


def tactics_search(
    filters: Annotated[TacticsSearchFilters, Depends()],
    use_case: Annotated[TacticsSearchUseCase, Depends(get_tactics_search_use_case)],
    limit: int = Query(20, ge=1, le=200),  # noqa: B008
) -> dict[str, object]:
    """Fetch recent tactics that match the given filters."""
    return use_case.search(filters, limit)
