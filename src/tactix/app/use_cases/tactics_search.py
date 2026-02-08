"""Use case for tactics search endpoints."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tactix.coerce_date_to_datetime__datetime import _coerce_date_to_datetime
from tactix.config import Settings, get_settings
from tactix.dashboard_query import DashboardQuery
from tactix.db.dashboard_repository_provider import fetch_recent_tactics
from tactix.db.duckdb_store import init_schema
from tactix.db.duckdb_unit_of_work import DuckDbUnitOfWork
from tactix.normalize_source__source import _normalize_source
from tactix.ports.unit_of_work import UnitOfWork
from tactix.tactics_search_filters import TacticsSearchFilters


@dataclass
class TacticsSearchUseCase:
    get_settings: Callable[..., Settings] = get_settings
    unit_of_work_factory: Callable[[Path], UnitOfWork] = DuckDbUnitOfWork
    init_schema: Callable[[Any], None] = init_schema
    fetch_recent_tactics: Callable[..., list[dict[str, object]]] = fetch_recent_tactics
    coerce_date_to_datetime: Callable[..., Any] = _coerce_date_to_datetime
    normalize_source: Callable[[str | None], str | None] = _normalize_source

    def search(self, filters: TacticsSearchFilters, limit: int) -> dict[str, object]:
        normalized_source = self.normalize_source(filters.source)
        settings = self.get_settings(source=normalized_source)
        start_datetime = self.coerce_date_to_datetime(filters.start_date)
        end_datetime = self.coerce_date_to_datetime(filters.end_date, end_of_day=True)
        uow = self.unit_of_work_factory(settings.duckdb_path)
        conn = uow.begin()
        try:
            self.init_schema(conn)
            tactics = self.fetch_recent_tactics(
                conn,
                DashboardQuery(
                    source=normalized_source,
                    motif=filters.motif,
                    rating_bucket=filters.rating_bucket,
                    time_control=filters.time_control,
                    start_date=start_datetime,
                    end_date=end_datetime,
                ),
                limit=limit,
            )
            response_source = "all" if normalized_source is None else normalized_source
            payload = {"source": response_source, "limit": limit, "tactics": tactics}
        except Exception:
            uow.rollback()
            raise
        else:
            uow.commit()
        finally:
            uow.close()
        return payload


def get_tactics_search_use_case() -> TacticsSearchUseCase:
    return TacticsSearchUseCase()


__all__ = ["TacticsSearchUseCase", "get_tactics_search_use_case"]
