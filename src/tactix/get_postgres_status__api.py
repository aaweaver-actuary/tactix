"""API endpoint for Postgres status payloads."""

from __future__ import annotations

from fastapi import Query

from tactix.config import get_settings
from tactix.db.postgres_repository import (
    PostgresRepository,
    default_postgres_repository_dependencies,
)
from tactix.serialize_status import serialize_status


def postgres_status(limit: int = Query(10, ge=1, le=50)) -> dict[str, object]:  # noqa: B008
    """Return Postgres status and recent ops events."""
    settings = get_settings()
    repo = PostgresRepository(
        settings,
        dependencies=default_postgres_repository_dependencies(),
    )
    status = repo.get_status()
    payload = serialize_status(status)
    payload["events"] = repo.fetch_ops_events(limit=limit)
    return payload
