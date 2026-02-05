from __future__ import annotations

from fastapi import Query

from tactix.api_logger__tactix import logger
from tactix.config import get_settings
from tactix.define_base_db_store_context__db_store import BaseDbStoreContext
from tactix.postgres_store_impl import PostgresStore


def postgres_analysis(limit: int = Query(10, ge=1, le=200)) -> dict[str, object]:  # noqa: B008
    settings = get_settings()
    store = PostgresStore(BaseDbStoreContext(settings=settings, logger=logger))
    tactics = store.fetch_analysis_tactics(limit=limit)
    return {"status": "ok", "tactics": tactics}
