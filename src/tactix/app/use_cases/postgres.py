"""Use cases for Postgres API endpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tactix.app.use_cases.dependencies import (
    DefaultPostgresRepositoryProvider,
    DefaultSettingsProvider,
    DefaultStatusSerializer,
    PostgresRepositoryProvider,
    SettingsProvider,
    StatusSerializer,
)


@dataclass
class PostgresUseCase:
    settings_provider: SettingsProvider = field(default_factory=DefaultSettingsProvider)
    repository_provider: PostgresRepositoryProvider = field(
        default_factory=DefaultPostgresRepositoryProvider
    )
    status_serializer: StatusSerializer = field(default_factory=DefaultStatusSerializer)

    def get_status(self, limit: int) -> dict[str, Any]:
        settings = self.settings_provider.get_settings()
        repo = self.repository_provider.create(settings)
        status = repo.get_status()
        payload = self.status_serializer.serialize(status)
        payload["events"] = repo.fetch_ops_events(limit=limit)
        return payload

    def get_analysis(self, limit: int) -> dict[str, object]:
        settings = self.settings_provider.get_settings()
        repo = self.repository_provider.create(settings)
        tactics = repo.fetch_analysis_tactics(limit=limit)
        return {"status": "ok", "tactics": tactics}

    def get_raw_pgns(self) -> dict[str, object]:
        settings = self.settings_provider.get_settings()
        repo = self.repository_provider.create(settings)
        return repo.fetch_raw_pgns_summary()


def get_postgres_use_case() -> PostgresUseCase:
    return PostgresUseCase()


__all__ = ["PostgresUseCase", "get_postgres_use_case"]
