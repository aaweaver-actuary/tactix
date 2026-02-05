"""API handler for Postgres raw PGN summaries."""

from __future__ import annotations

from tactix.config import get_settings
from tactix.db.postgres_repository import (
    PostgresRepository,
    default_postgres_repository_dependencies,
)


def postgres_raw_pgns() -> dict[str, object]:
    """Return the raw PGN summary from Postgres."""
    settings = get_settings()
    repo = PostgresRepository(
        settings,
        dependencies=default_postgres_repository_dependencies(),
    )
    return repo.fetch_raw_pgns_summary()
