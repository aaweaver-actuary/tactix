"""API handler for practice attempt submissions."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from tactix.app.use_cases.practice import (
    PracticeAttemptError,
    PracticeUseCase,
    get_practice_use_case,
)
from tactix.models import PracticeAttemptRequest


def practice_attempt(
    payload: PracticeAttemptRequest,
    use_case: Annotated[PracticeUseCase, Depends(get_practice_use_case)],
) -> dict[str, object]:
    """Grade a practice attempt and return the result."""
    try:
        return use_case.submit_attempt(payload)
    except PracticeAttemptError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
