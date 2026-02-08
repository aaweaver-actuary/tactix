"""Use case for pipeline run endpoints."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from tactix.app.use_cases.dependencies import (
    CacheRefresher,
    DashboardRepositoryFactory,
    DateTimeCoercer,
    PipelineRunner,
    SettingsProvider,
    SourceNormalizer,
    UnitOfWorkRunner,
)
from tactix.app.wiring import (
    DefaultCacheRefresher,
    DefaultDashboardRepositoryFactory,
    DefaultDateTimeCoercer,
    DefaultPipelineRunner,
    DefaultSettingsProvider,
    DefaultSourceNormalizer,
    DuckDbUnitOfWorkRunner,
)
from tactix.config import Settings
from tactix.dashboard_query import DashboardQuery
from tactix.pipeline_run_filters import PipelineRunFilters
from tactix.trace_context import trace_context


class PipelineWindowError(ValueError):
    """Raised when a pipeline run window is invalid."""


@dataclass
class PipelineRunUseCase:  # pylint: disable=too-many-instance-attributes
    settings_provider: SettingsProvider = field(default_factory=DefaultSettingsProvider)
    source_normalizer: SourceNormalizer = field(default_factory=DefaultSourceNormalizer)
    date_time_coercer: DateTimeCoercer = field(default_factory=DefaultDateTimeCoercer)
    pipeline_runner: PipelineRunner = field(default_factory=DefaultPipelineRunner)
    cache_refresher: CacheRefresher = field(default_factory=DefaultCacheRefresher)
    dashboard_repository_factory: DashboardRepositoryFactory = field(
        default_factory=DefaultDashboardRepositoryFactory
    )
    uow_runner: UnitOfWorkRunner = field(default_factory=DuckDbUnitOfWorkRunner)

    def run(self, filters: PipelineRunFilters) -> dict[str, object]:
        normalized_source = self.source_normalizer.normalize(filters.source)
        settings = self._resolve_pipeline_settings(normalized_source, filters)
        run_id = uuid4().hex
        settings.run_id = run_id
        start_datetime, end_datetime, window_start_ms, window_end_ms = self._resolve_window_range(
            filters
        )
        with trace_context(run_id=run_id, op_id="pipeline.run"):
            result = self.pipeline_runner.run(
                settings,
                source=normalized_source,
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
                profile=None,
            )
            self.cache_refresher.refresh(
                self.cache_refresher.sources_for_refresh(normalized_source)
            )
            counts, motif_counts = self._fetch_pipeline_counts(
                settings.duckdb_path,
                DashboardQuery(
                    source=normalized_source,
                    start_date=start_datetime,
                    end_date=end_datetime,
                ),
            )
        return {
            "status": "ok",
            "run_id": run_id,
            "result": result,
            "counts": counts,
            "motif_counts": motif_counts,
            "window_start_ms": window_start_ms,
            "window_end_ms": window_end_ms,
        }

    def _fetch_pipeline_counts(
        self,
        db_path: Path,
        query: DashboardQuery,
    ) -> tuple[dict[str, int], dict[str, int]]:
        def handler(conn: Any) -> tuple[dict[str, int], dict[str, int]]:
            repo = self.dashboard_repository_factory.create(conn)
            counts = repo.fetch_pipeline_table_counts(query)
            motif_counts = repo.fetch_opportunity_motif_counts(query)
            return counts, motif_counts

        return self.uow_runner.run(db_path, handler)

    def _resolve_pipeline_settings(
        self,
        normalized_source: str | None,
        filters: PipelineRunFilters,
    ) -> Settings:
        settings = self.settings_provider.get_settings(
            source=normalized_source,
            profile=filters.profile,
        )
        self._apply_user_settings(settings, filters.user_id)
        self._apply_fixture_settings(settings, filters.use_fixture, filters.fixture_name)
        self._apply_db_settings(settings, filters.db_name, filters.reset_db)
        return settings

    def _apply_user_settings(self, settings: Settings, user_id: str | None) -> None:
        if not user_id:
            return
        settings.user = user_id
        settings.lichess.user = user_id
        settings.chesscom.user = user_id

    def _apply_fixture_settings(
        self,
        settings: Settings,
        use_fixture: bool,
        fixture_name: str | None,
    ) -> None:
        if not self._should_apply_fixture(use_fixture, fixture_name):
            return
        self._apply_fixture_flags(settings)
        self._resolve_stockfish_path(settings)
        self._apply_fixture_paths_if_needed(settings, fixture_name)

    def _should_apply_fixture(self, use_fixture: bool, fixture_name: str | None) -> bool:
        return bool(use_fixture or fixture_name)

    def _apply_fixture_flags(self, settings: Settings) -> None:
        settings.chesscom.token = None
        settings.lichess.token = None
        settings.use_fixture_when_no_token = True
        settings.chesscom_use_fixture_when_no_token = True
        settings.stockfish_movetime_ms = 60
        settings.stockfish_depth = 8
        settings.stockfish_multipv = 2

    def _resolve_stockfish_path(self, settings: Settings) -> None:
        resolved_stockfish = shutil.which(str(settings.stockfish_path)) or shutil.which("stockfish")
        if resolved_stockfish:
            settings.stockfish_path = Path(resolved_stockfish)

    def _apply_fixture_paths(self, settings: Settings, fixture_name: str) -> None:
        safe_name = Path(fixture_name).name
        repo_root = Path(__file__).resolve().parents[4]
        settings.fixture_pgn_path = repo_root / "tests" / "fixtures" / safe_name
        settings.chesscom_fixture_pgn_path = repo_root / "tests" / "fixtures" / safe_name
        settings.lichess_token_cache_path = settings.lichess_token_cache_path.with_name(
            "lichess_token_fixture.json"
        )

    def _apply_fixture_paths_if_needed(
        self,
        settings: Settings,
        fixture_name: str | None,
    ) -> None:
        if fixture_name:
            self._apply_fixture_paths(settings, fixture_name)

    def _apply_db_settings(self, settings: Settings, db_name: str | None, reset_db: bool) -> None:
        if not db_name:
            return
        safe_name = Path(db_name).name
        filename = safe_name if safe_name.endswith(".duckdb") else f"{safe_name}.duckdb"
        settings.duckdb_path = settings.data_dir / filename
        if reset_db and settings.duckdb_path.exists():
            settings.duckdb_path.unlink()

    def _resolve_window_range(
        self,
        filters: PipelineRunFilters,
    ) -> tuple[datetime | None, datetime | None, int | None, int | None]:
        start_datetime = self.date_time_coercer.coerce(filters.start_date)
        end_datetime = self.date_time_coercer.coerce(filters.end_date, end_of_day=True)
        window_start_ms = self._datetime_to_ms(start_datetime)
        window_end_ms = self._datetime_to_ms(end_datetime)
        if window_end_ms is not None:
            window_end_ms += 1
        if (
            window_start_ms is not None
            and window_end_ms is not None
            and window_start_ms >= window_end_ms
        ):
            raise PipelineWindowError("start_date must be before end_date")
        return start_datetime, end_datetime, window_start_ms, window_end_ms

    def _datetime_to_ms(self, value: datetime | None) -> int | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return int(value.timestamp() * 1000)


def get_pipeline_run_use_case() -> PipelineRunUseCase:
    return PipelineRunUseCase()


__all__ = ["PipelineRunUseCase", "PipelineWindowError", "get_pipeline_run_use_case"]
