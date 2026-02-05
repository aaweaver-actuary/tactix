"""API endpoint for Postgres status payloads."""

from __future__ import annotations

from fastapi import Query

from tactix.api_logger__tactix import logger
from tactix.config import get_settings
from tactix.define_base_db_store_context__db_store import BaseDbStoreContext
from tactix.postgres_store_impl import PostgresStore
from tactix.serialize_status import serialize_status


def postgres_status(limit: int = Query(10, ge=1, le=50)) -> dict[str, object]:  # noqa: B008
    """Return Postgres status and recent ops events."""
    settings = get_settings()
    store = PostgresStore(BaseDbStoreContext(settings=settings, logger=logger))
    status = store.get_status()
    payload = serialize_status(status)
    payload["events"] = store.fetch_ops_events(limit=limit)
    return payload
