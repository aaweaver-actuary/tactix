"""API endpoint to fetch the practice queue."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from tactix.app.use_cases.practice import PracticeUseCase, get_practice_use_case


def practice_queue(
    use_case: Annotated[PracticeUseCase, Depends(get_practice_use_case)],
    source: Annotated[str | None, Query()] = None,
    include_failed_attempt: bool = Query(False),  # noqa: B008
    limit: int = Query(20, ge=1, le=200),  # noqa: B008
) -> dict[str, object]:
    """Fetch a practice queue payload for the requested source."""
    return use_case.get_queue(
        source=source,
        include_failed_attempt=include_failed_attempt,
        limit=limit,
    )
