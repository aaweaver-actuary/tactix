"""Use cases for practice-related API endpoints."""

from __future__ import annotations

import time as time_module
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tactix.config import Settings, get_settings
from tactix.db.duckdb_store import init_schema
from tactix.db.duckdb_unit_of_work import DuckDbUnitOfWork
from tactix.db.tactic_repository_provider import tactic_repository
from tactix.models import PracticeAttemptRequest
from tactix.normalize_source__source import _normalize_source
from tactix.ports.unit_of_work import UnitOfWork


class PracticeAttemptError(ValueError):
    """Raised when a practice attempt cannot be graded."""


class GameNotFoundError(LookupError):
    """Raised when a game detail payload is missing a PGN."""


@dataclass
class PracticeUseCase:
    get_settings: Callable[..., Settings] = get_settings
    unit_of_work_factory: Callable[[Path], UnitOfWork] = DuckDbUnitOfWork
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
        uow = self.unit_of_work_factory(settings.duckdb_path)
        conn = uow.begin()
        try:
            self.init_schema(conn)
            queue = self.repository_factory(conn).fetch_practice_queue(
                limit=limit,
                source=normalized_source or settings.source,
                include_failed_attempt=include_failed_attempt,
            )
            payload = {
                "source": normalized_source or settings.source,
                "include_failed_attempt": include_failed_attempt,
                "items": queue,
            }
        except Exception:
            uow.rollback()
            raise
        else:
            uow.commit()
        finally:
            uow.close()
        return payload

    def get_next(
        self,
        source: str | None,
        include_failed_attempt: bool,
    ) -> dict[str, object]:
        normalized_source = self.normalize_source(source)
        settings = self.get_settings(source=normalized_source)
        uow = self.unit_of_work_factory(settings.duckdb_path)
        conn = uow.begin()
        try:
            self.init_schema(conn)
            items = self.repository_factory(conn).fetch_practice_queue(
                limit=1,
                source=normalized_source or settings.source,
                include_failed_attempt=include_failed_attempt,
                exclude_seen=True,
            )
            payload = {
                "source": normalized_source or settings.source,
                "include_failed_attempt": include_failed_attempt,
                "item": items[0] if items else None,
            }
        except Exception:
            uow.rollback()
            raise
        else:
            uow.commit()
        finally:
            uow.close()
        return payload

    def submit_attempt(self, payload: PracticeAttemptRequest) -> dict[str, object]:
        settings = self.get_settings(source=payload.source)
        uow = self.unit_of_work_factory(settings.duckdb_path)
        conn = uow.begin()
        latency_ms = self._resolve_latency_ms(payload.served_at_ms)
        try:
            self.init_schema(conn)
            repo = self.repository_factory(conn)
            result = repo.grade_practice_attempt(
                payload.tactic_id,
                payload.position_id,
                payload.attempted_uci,
                latency_ms=latency_ms,
            )
        except ValueError as exc:
            uow.rollback()
            raise PracticeAttemptError(str(exc)) from exc
        except Exception:
            uow.rollback()
            raise
        else:
            uow.commit()
        finally:
            uow.close()
        return result

    def get_game_detail(self, game_id: str, source: str | None) -> dict[str, object]:
        normalized_source = self.normalize_source(source)
        settings = self.get_settings(source=normalized_source)
        uow = self.unit_of_work_factory(settings.duckdb_path)
        conn = uow.begin()
        try:
            self.init_schema(conn)
            payload = self.repository_factory(conn).fetch_game_detail(
                game_id,
                settings.user,
                normalized_source,
            )
        except Exception:
            uow.rollback()
            raise
        else:
            uow.commit()
        finally:
            uow.close()
        if not payload.get("pgn"):
            raise GameNotFoundError("Game not found")
        return payload

    def _resolve_latency_ms(self, served_at_ms: int | None) -> int | None:
        if served_at_ms is None:
            return None
        now_ms = int(self.time_provider() * 1000)
        return max(0, now_ms - served_at_ms)


def get_practice_use_case() -> PracticeUseCase:
    return PracticeUseCase()


__all__ = [
    "GameNotFoundError",
    "PracticeAttemptError",
    "PracticeUseCase",
    "get_practice_use_case",
]
