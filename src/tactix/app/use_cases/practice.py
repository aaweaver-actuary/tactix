"""Use cases for practice-related API endpoints."""

from __future__ import annotations

import time as time_module
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tactix.config import Settings, get_settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.tactic_repository_provider import tactic_repository
from tactix.models import PracticeAttemptRequest
from tactix.normalize_source__source import _normalize_source


class PracticeAttemptError(ValueError):
    """Raised when a practice attempt cannot be graded."""


class GameNotFoundError(LookupError):
    """Raised when a game detail payload is missing a PGN."""


@dataclass
class PracticeUseCase:
    get_settings: Callable[..., Settings] = get_settings
    get_connection: Callable[[Path], Any] = get_connection
    init_schema: Callable[[Any], None] = init_schema
    repository_factory: Callable[[Any], Any] = tactic_repository
    normalize_source: Callable[[str | None], str | None] = _normalize_source
    time_provider: Callable[[], float] = time_module.time

    def get_queue(
        self,
        source: str | None,
        include_failed_attempt: bool,
        limit: int,
    ) -> dict[str, object]:
        normalized_source = self.normalize_source(source)
        settings = self.get_settings(source=normalized_source)
        conn = self.get_connection(settings.duckdb_path)
        self.init_schema(conn)
        queue = self.repository_factory(conn).fetch_practice_queue(
            limit=limit,
            source=normalized_source or settings.source,
            include_failed_attempt=include_failed_attempt,
        )
        return {
            "source": normalized_source or settings.source,
            "include_failed_attempt": include_failed_attempt,
            "items": queue,
        }

    def get_next(
        self,
        source: str | None,
        include_failed_attempt: bool,
    ) -> dict[str, object]:
        normalized_source = self.normalize_source(source)
        settings = self.get_settings(source=normalized_source)
        conn = self.get_connection(settings.duckdb_path)
        self.init_schema(conn)
        items = self.repository_factory(conn).fetch_practice_queue(
            limit=1,
            source=normalized_source or settings.source,
            include_failed_attempt=include_failed_attempt,
            exclude_seen=True,
        )
        return {
            "source": normalized_source or settings.source,
            "include_failed_attempt": include_failed_attempt,
            "item": items[0] if items else None,
        }

    def submit_attempt(self, payload: PracticeAttemptRequest) -> dict[str, object]:
        settings = self.get_settings(source=payload.source)
        conn = self.get_connection(settings.duckdb_path)
        self.init_schema(conn)
        latency_ms: int | None = None
        if payload.served_at_ms is not None:
            now_ms = int(self.time_provider() * 1000)
            latency_ms = max(0, now_ms - payload.served_at_ms)
        try:
            repo = self.repository_factory(conn)
            return repo.grade_practice_attempt(
                payload.tactic_id,
                payload.position_id,
                payload.attempted_uci,
                latency_ms=latency_ms,
            )
        except ValueError as exc:
            raise PracticeAttemptError(str(exc)) from exc

    def get_game_detail(self, game_id: str, source: str | None) -> dict[str, object]:
        normalized_source = self.normalize_source(source)
        settings = self.get_settings(source=normalized_source)
        conn = self.get_connection(settings.duckdb_path)
        self.init_schema(conn)
        payload = self.repository_factory(conn).fetch_game_detail(
            game_id,
            settings.user,
            normalized_source,
        )
        if not payload.get("pgn"):
            raise GameNotFoundError("Game not found")
        return payload


def get_practice_use_case() -> PracticeUseCase:
    return PracticeUseCase()


__all__ = [
    "GameNotFoundError",
    "PracticeAttemptError",
    "PracticeUseCase",
    "get_practice_use_case",
]
