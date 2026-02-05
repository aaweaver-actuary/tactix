"""Legacy shim for Postgres store access."""

from __future__ import annotations

from tactix.db.postgres_repository import (
    PostgresRepository,
    default_postgres_repository_dependencies,
)

__all__ = [
    "PostgresRepository",
    "default_postgres_repository_dependencies",
]
