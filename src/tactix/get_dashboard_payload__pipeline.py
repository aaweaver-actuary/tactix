from __future__ import annotations

from datetime import datetime

from tactix.base_db_store import BaseDbStore, BaseDbStoreContext
from tactix.config import Settings, get_settings
from tactix.db.duckdb_store import DuckDbStore
from tactix.pipeline_state__pipeline import logger


def get_dashboard_payload(
    settings: Settings | None = None,
    source: str | None = None,
    motif: str | None = None,
    rating_bucket: str | None = None,
    time_control: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    store: BaseDbStore | None = None,
) -> dict[str, object]:
    normalized_source = None if source in (None, "all") else source
    settings = settings or get_settings(source=normalized_source)
    if normalized_source:
        settings.source = normalized_source
    settings.apply_source_defaults()
    if store is None:
        store = DuckDbStore(
            BaseDbStoreContext(settings=settings, logger=logger),
            db_path=settings.duckdb_path,
        )
    return store.get_dashboard_payload(
        source=normalized_source,
        motif=motif,
        rating_bucket=rating_bucket,
        time_control=time_control,
        start_date=start_date,
        end_date=end_date,
    )
