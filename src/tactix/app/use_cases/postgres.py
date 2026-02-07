"""Use cases for Postgres API endpoints."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tactix.config import Settings, get_settings
from tactix.db.postgres_repository import (
    PostgresRepository,
    default_postgres_repository_dependencies,
)
from tactix.postgres_status import PostgresStatus
from tactix.serialize_status import serialize_status


def _default_postgres_repository(settings: Settings) -> PostgresRepository:
    return PostgresRepository(
        settings,
        dependencies=default_postgres_repository_dependencies(),
    )


@dataclass
class PostgresUseCase:
    get_settings: Callable[[], Settings] = get_settings
    repository_factory: Callable[[Settings], PostgresRepository] = _default_postgres_repository
    serialize_status: Callable[[PostgresStatus], dict[str, Any]] = serialize_status

    def get_status(self, limit: int) -> dict[str, Any]:
        settings = self.get_settings()
        repo = self.repository_factory(settings)
        status = repo.get_status()
        payload = self.serialize_status(status)
        payload["events"] = repo.fetch_ops_events(limit=limit)
        return payload

    def get_analysis(self, limit: int) -> dict[str, object]:
        settings = self.get_settings()
        repo = self.repository_factory(settings)
        tactics = repo.fetch_analysis_tactics(limit=limit)
        return {"status": "ok", "tactics": tactics}

    def get_raw_pgns(self) -> dict[str, object]:
        settings = self.get_settings()
        repo = self.repository_factory(settings)
        return repo.fetch_raw_pgns_summary()


def get_postgres_use_case() -> PostgresUseCase:
    return PostgresUseCase()


__all__ = ["PostgresUseCase", "get_postgres_use_case"]
