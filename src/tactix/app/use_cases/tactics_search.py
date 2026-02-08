"""Use case for tactics search endpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tactix.app.use_cases.dependencies import (
    DashboardRepositoryFactory,
    DateTimeCoercer,
    DefaultDashboardRepositoryFactory,
    DefaultDateTimeCoercer,
    DefaultSettingsProvider,
    DefaultSourceNormalizer,
    DuckDbUnitOfWorkRunner,
    SettingsProvider,
    SourceNormalizer,
    UnitOfWorkRunner,
)
from tactix.config import Settings
from tactix.dashboard_query import DashboardQuery
from tactix.tactics_search_filters import TacticsSearchFilters


@dataclass
class TacticsSearchUseCase:
    settings_provider: SettingsProvider = field(default_factory=DefaultSettingsProvider)
    source_normalizer: SourceNormalizer = field(default_factory=DefaultSourceNormalizer)
    date_time_coercer: DateTimeCoercer = field(default_factory=DefaultDateTimeCoercer)
    dashboard_repository_factory: DashboardRepositoryFactory = field(
        default_factory=DefaultDashboardRepositoryFactory
    )
    uow_runner: UnitOfWorkRunner = field(default_factory=DuckDbUnitOfWorkRunner)

    def search(self, filters: TacticsSearchFilters, limit: int) -> dict[str, object]:
        normalized_source = self.source_normalizer.normalize(filters.source)
        settings = self.settings_provider.get_settings(source=normalized_source)
        start_datetime = self.date_time_coercer.coerce(filters.start_date)
        end_datetime = self.date_time_coercer.coerce(filters.end_date, end_of_day=True)

        def handler(conn: Any) -> dict[str, object]:
            repo = self.dashboard_repository_factory.create(conn)
            tactics = repo.fetch_recent_tactics(
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
            return {"source": response_source, "limit": limit, "tactics": tactics}

        return self.uow_runner.run(settings.duckdb_path, handler)


def get_tactics_search_use_case() -> TacticsSearchUseCase:
    return TacticsSearchUseCase()


__all__ = ["TacticsSearchUseCase", "get_tactics_search_use_case"]
