from __future__ import annotations

from tactix.api_logger__tactix import logger
from tactix.base_db_store import BaseDbStoreContext
from tactix.config import get_settings
from tactix.PostgresStore import PostgresStore


def postgres_raw_pgns() -> dict[str, object]:
    settings = get_settings()
    store = PostgresStore(BaseDbStoreContext(settings=settings, logger=logger))
    return store.fetch_raw_pgns_summary()
