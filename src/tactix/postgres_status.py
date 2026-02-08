"""Postgres health status models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PostgresStatus:
    """Status snapshot for Postgres connectivity checks."""

    enabled: bool
    status: str
    latency_ms: float | None = None
    error: str | None = None
    schema: str | None = None
    tables: list[str] | None = None
