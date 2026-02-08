from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from tactix.app.use_cases.postgres import PostgresUseCase, get_postgres_use_case


def postgres_analysis(
    use_case: Annotated[PostgresUseCase, Depends(get_postgres_use_case)],
    limit: int = Query(10, ge=1, le=200),  # noqa: B008
) -> dict[str, object]:
    return use_case.get_analysis(limit)
