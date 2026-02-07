"""API handler for Postgres raw PGN summaries."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from tactix.app.use_cases.postgres import PostgresUseCase, get_postgres_use_case


def postgres_raw_pgns(
    use_case: Annotated[PostgresUseCase, Depends(get_postgres_use_case)],
) -> dict[str, object]:
    """Return the raw PGN summary from Postgres."""
    return use_case.get_raw_pgns()
