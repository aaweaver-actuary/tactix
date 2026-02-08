"""API endpoint for Postgres status payloads."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from tactix.app.use_cases.postgres import PostgresUseCase, get_postgres_use_case


def postgres_status(
    use_case: Annotated[PostgresUseCase, Depends(get_postgres_use_case)],
    limit: int = Query(10, ge=1, le=50),  # noqa: B008
) -> dict[str, object]:
    """Return Postgres status and recent ops events."""
    return use_case.get_status(limit)
