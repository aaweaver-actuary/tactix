"""API endpoint for Postgres status payloads."""

from __future__ import annotations

from fastapi import Query

from tactix.api_logger__tactix import logger
from tactix.base_db_store import BaseDbStoreContext
from tactix.config import get_settings
from tactix.PostgresStore import PostgresStore
from tactix.serialize_status import serialize_status


def postgres_status(limit: int = Query(10, ge=1, le=50)) -> dict[str, object]:  # noqa: B008
    """Return Postgres status and recent ops events."""
    settings = get_settings()
    store = PostgresStore(BaseDbStoreContext(settings=settings, logger=logger))
    status = store.get_status()
    payload = serialize_status(status)
    payload["events"] = store.fetch_ops_events(limit=limit)
    return payload
