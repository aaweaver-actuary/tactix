"""API endpoint for the next practice item."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from tactix.app.use_cases.practice import PracticeUseCase, get_practice_use_case


def practice_next(
    use_case: Annotated[PracticeUseCase, Depends(get_practice_use_case)],
    source: Annotated[str | None, Query()] = None,
    include_failed_attempt: bool = Query(False),  # noqa: B008
) -> dict[str, object]:
    """Fetch the next practice item for the requested source."""
    return use_case.get_next(
        source=source,
        include_failed_attempt=include_failed_attempt,
    )
