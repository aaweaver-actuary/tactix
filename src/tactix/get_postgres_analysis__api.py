from __future__ import annotations

from fastapi import Query

from tactix.config import get_settings
from tactix.db.postgres_repository import (
    PostgresRepository,
    default_postgres_repository_dependencies,
)


def postgres_analysis(limit: int = Query(10, ge=1, le=200)) -> dict[str, object]:  # noqa: B008
    settings = get_settings()
    repo = PostgresRepository(
        settings,
        dependencies=default_postgres_repository_dependencies(),
    )
    tactics = repo.fetch_analysis_tactics(limit=limit)
    return {"status": "ok", "tactics": tactics}
