"""Use cases for practice-related API endpoints."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from tactix.app.use_cases.dependencies import (
    Clock,
    SettingsProvider,
    SourceNormalizer,
    TacticRepositoryFactory,
    UnitOfWorkRunner,
)
from tactix.app.wiring import (
    DefaultClock,
    DefaultSettingsProvider,
    DefaultSourceNormalizer,
    DefaultTacticRepositoryFactory,
    DuckDbUnitOfWorkRunner,
)
from tactix.config import Settings
from tactix.models import PracticeAttemptRequest


class PracticeAttemptError(ValueError):
    """Raised when a practice attempt cannot be graded."""


class GameNotFoundError(LookupError):
    """Raised when a game detail payload is missing a PGN."""


def _missing_uow_runner() -> UnitOfWorkRunner:
    raise ValueError("uow_runner is required for PracticeUseCase")


@dataclass(frozen=True)
class PracticeQueueRequest:
    """Inputs for fetching practice queue items."""

    normalized_source: str | None
    include_failed_attempt: bool
    settings: Settings
    limit: int
    exclude_seen: bool = False


@dataclass
class PracticeUseCase:
    settings_provider: SettingsProvider = field(default_factory=DefaultSettingsProvider)
    source_normalizer: SourceNormalizer = field(default_factory=DefaultSourceNormalizer)
    repository_factory: TacticRepositoryFactory = field(
        default_factory=DefaultTacticRepositoryFactory
    )
    uow_runner: UnitOfWorkRunner = field(default_factory=_missing_uow_runner)
    clock: Clock = field(default_factory=DefaultClock)

    def get_queue(
        self,
        source: str | None,
        include_failed_attempt: bool,
        limit: int,
    ) -> dict[str, object]:
        request = self._build_queue_request(source, include_failed_attempt, limit)
        return self._run_with_uow(
            request.settings,
            lambda conn: self._queue_payload(request, self._fetch_queue_items(conn, request)),
        )

    def get_next(
        self,
        source: str | None,
        include_failed_attempt: bool,
    ) -> dict[str, object]:
        request = self._build_queue_request(
            source,
            include_failed_attempt,
            limit=1,
            exclude_seen=True,
        )
        return self._run_with_uow(
            request.settings,
            lambda conn: self._next_payload(request, self._fetch_queue_items(conn, request)),
        )

    def submit_attempt(self, payload: PracticeAttemptRequest) -> dict[str, object]:
        settings = self.settings_provider.get_settings(source=payload.source)
        latency_ms = self._resolve_latency_ms(payload.served_at_ms)
        try:
            return self._run_with_uow(
                settings,
                lambda conn: self._grade_attempt(conn, payload, latency_ms),
            )
        except ValueError as exc:
            raise PracticeAttemptError(str(exc)) from exc

    def get_game_detail(self, game_id: str, source: str | None) -> dict[str, object]:
        normalized_source, settings = self._resolve_settings_for_source(source)
        payload = self._run_with_uow(
            settings,
            lambda conn: self.repository_factory.create(conn).fetch_game_detail(
                game_id,
                settings.user,
                normalized_source,
            ),
        )
        if not payload.get("pgn"):
            raise GameNotFoundError("Game not found")
        return payload

    def _fetch_queue_items(
        self,
        conn: Any,
        request: PracticeQueueRequest,
    ) -> list[dict[str, object]]:
        return self.repository_factory.create(conn).fetch_practice_queue(
            limit=request.limit,
            source=request.normalized_source or request.settings.source,
            include_failed_attempt=request.include_failed_attempt,
            exclude_seen=request.exclude_seen,
        )

    def _queue_payload(
        self,
        request: PracticeQueueRequest,
        items: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "source": request.normalized_source or request.settings.source,
            "include_failed_attempt": request.include_failed_attempt,
            "items": items,
        }

    def _next_payload(
        self,
        request: PracticeQueueRequest,
        items: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "source": request.normalized_source or request.settings.source,
            "include_failed_attempt": request.include_failed_attempt,
            "item": items[0] if items else None,
        }

    def _grade_attempt(
        self,
        conn: Any,
        payload: PracticeAttemptRequest,
        latency_ms: int | None,
    ) -> dict[str, object]:
        repo = self.repository_factory.create(conn)
        return repo.grade_practice_attempt(
            payload.tactic_id,
            payload.position_id,
            payload.attempted_uci,
            latency_ms=latency_ms,
        )

    def _run_with_uow(
        self,
        settings: Settings,
        handler: Callable[[Any], dict[str, object]],
    ) -> dict[str, object]:
        return self.uow_runner.run(settings.duckdb_path, handler)

    def _resolve_latency_ms(self, served_at_ms: int | None) -> int | None:
        if served_at_ms is None:
            return None
        now_ms = int(self.clock.now() * 1000)
        return max(0, now_ms - served_at_ms)

    def _resolve_settings_for_source(self, source: str | None) -> tuple[str | None, Settings]:
        normalized_source = self.source_normalizer.normalize(source)
        settings = self.settings_provider.get_settings(source=normalized_source)
        return normalized_source, settings

    def _build_queue_request(
        self,
        source: str | None,
        include_failed_attempt: bool,
        limit: int,
        exclude_seen: bool = False,
    ) -> PracticeQueueRequest:
        normalized_source, settings = self._resolve_settings_for_source(source)
        return PracticeQueueRequest(
            normalized_source=normalized_source,
            include_failed_attempt=include_failed_attempt,
            settings=settings,
            limit=limit,
            exclude_seen=exclude_seen,
        )


def get_practice_use_case() -> PracticeUseCase:
    return PracticeUseCase(uow_runner=DuckDbUnitOfWorkRunner())


__all__ = [
    "GameNotFoundError",
    "PracticeAttemptError",
    "PracticeUseCase",
    "get_practice_use_case",
]
