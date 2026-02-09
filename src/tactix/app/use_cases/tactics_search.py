"""Use case for tactics search endpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tactix.app.use_cases.dependencies import (
    DashboardRepositoryFactory,
    DateTimeCoercer,
    SettingsProvider,
    SourceNormalizer,
    UnitOfWorkRunner,
)
from tactix.app.wiring import (
    DefaultDashboardRepositoryFactory,
    DefaultDateTimeCoercer,
    DefaultSettingsProvider,
    DefaultSourceNormalizer,
    DuckDbUnitOfWorkRunner,
)
from tactix.dashboard_query import DashboardQuery
from tactix.tactic_scope import is_allowed_motif_filter
from tactix.tactics_search_filters import TacticsSearchFilters


def _missing_uow_runner() -> UnitOfWorkRunner:
    raise ValueError("uow_runner is required for TacticsSearchUseCase")


def _normalize_motif_filter(motif: str | None) -> str | None:
    normalized = (motif or "").strip().lower()
    if normalized in {"", "all", "any"}:
        return None
    return normalized


def _response_source(normalized_source: str | None) -> str:
    return "all" if normalized_source is None else normalized_source


def _empty_search_response(normalized_source: str | None, limit: int) -> dict[str, object]:
    return {"source": _response_source(normalized_source), "limit": limit, "tactics": []}


@dataclass
class TacticsSearchUseCase:
    settings_provider: SettingsProvider = field(default_factory=DefaultSettingsProvider)
    source_normalizer: SourceNormalizer = field(default_factory=DefaultSourceNormalizer)
    date_time_coercer: DateTimeCoercer = field(default_factory=DefaultDateTimeCoercer)
    dashboard_repository_factory: DashboardRepositoryFactory = field(
        default_factory=DefaultDashboardRepositoryFactory
    )
    uow_runner: UnitOfWorkRunner = field(default_factory=_missing_uow_runner)

    def search(self, filters: TacticsSearchFilters, limit: int) -> dict[str, object]:
        normalized_source = self.source_normalizer.normalize(filters.source)
        settings = self.settings_provider.get_settings(source=normalized_source)
        motif_value = _normalize_motif_filter(filters.motif)
        if motif_value and not is_allowed_motif_filter(motif_value):
            return _empty_search_response(normalized_source, limit)
        start_datetime = self.date_time_coercer.coerce(filters.start_date)
        end_datetime = self.date_time_coercer.coerce(filters.end_date, end_of_day=True)

        def handler(conn: Any) -> dict[str, object]:
            repo = self.dashboard_repository_factory.create(conn)
            tactics = repo.fetch_recent_tactics(
                DashboardQuery(
                    source=normalized_source,
                    motif=motif_value,
                    rating_bucket=filters.rating_bucket,
                    time_control=filters.time_control,
                    start_date=start_datetime,
                    end_date=end_datetime,
                ),
                limit=limit,
            )
            return {
                "source": _response_source(normalized_source),
                "limit": limit,
                "tactics": tactics,
            }

        return self.uow_runner.run(settings.duckdb_path, handler)


def get_tactics_search_use_case() -> TacticsSearchUseCase:
    return TacticsSearchUseCase(uow_runner=DuckDbUnitOfWorkRunner())


__all__ = ["TacticsSearchUseCase", "get_tactics_search_use_case"]
