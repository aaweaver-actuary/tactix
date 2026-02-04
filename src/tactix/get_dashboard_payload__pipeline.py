from __future__ import annotations

from tactix.base_db_store import BaseDbStore, BaseDbStoreContext
from tactix.config import Settings, get_settings
from tactix.dashboard_query import DashboardQuery
from tactix.db.duckdb_store import DuckDbStore
from tactix.pipeline_state__pipeline import logger


def get_dashboard_payload(
    query: DashboardQuery | None = None,
    settings: Settings | None = None,
    store: BaseDbStore | None = None,
) -> dict[str, object]:
    query = query or DashboardQuery()
    normalized_source = None if query.source in (None, "all") else query.source
    settings = _resolve_dashboard_settings(settings, normalized_source)
    if store is None:
        store = DuckDbStore(
            BaseDbStoreContext(settings=settings, logger=logger),
            db_path=settings.duckdb_path,
        )
    return store.get_dashboard_payload(
        DashboardQuery(
            source=normalized_source,
            motif=query.motif,
            rating_bucket=query.rating_bucket,
            time_control=query.time_control,
            start_date=query.start_date,
            end_date=query.end_date,
        )
    )


def _resolve_dashboard_settings(
    settings: Settings | None,
    normalized_source: str | None,
) -> Settings:
    resolved = settings or get_settings(source=normalized_source)
    if normalized_source:
        resolved.source = normalized_source
    resolved.apply_source_defaults()
    return resolved
