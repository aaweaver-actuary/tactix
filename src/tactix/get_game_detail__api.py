"""API handler for game detail retrieval."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Query

from tactix.app.use_cases.practice import (
    GameNotFoundError,
    PracticeUseCase,
    get_practice_use_case,
)


def game_detail(
    game_id: str,
    use_case: Annotated[PracticeUseCase, Depends(get_practice_use_case)],
    source: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    """Return game detail payload for a game id."""
    try:
        return use_case.get_game_detail(game_id, source)
    except GameNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
