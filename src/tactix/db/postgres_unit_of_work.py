"""Postgres unit-of-work implementation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import psycopg2
from psycopg2.extensions import connection as PgConnection  # noqa: N812

from tactix._connection_kwargs import _connection_kwargs
from tactix.config import Settings
from tactix.ports.unit_of_work import UnitOfWork
from tactix.utils.logger import Logger

logger = Logger(__name__)


@dataclass
class PostgresUnitOfWork(UnitOfWork[PgConnection]):
    """Manage a Postgres session with explicit transaction boundaries."""

    settings: Settings
    connection_factory: Callable[..., PgConnection] = psycopg2.connect
    _conn: PgConnection | None = None
    _active: bool = False

    def begin(self) -> PgConnection | None:
        if self._conn is not None:
            return self._conn
        kwargs = _connection_kwargs(self.settings)
        if not kwargs:
            return None
        try:
            self._conn = self.connection_factory(**kwargs)
        except Exception as exc:  # pragma: no cover - handled by status endpoint
            logger.warning("Postgres connection failed: %s", exc)
            self._conn = None
            self._active = False
            return None
        self._conn.autocommit = False
        self._active = True
        return self._conn

    def commit(self) -> None:
        if self._conn is None or not self._active:
            return
        self._conn.commit()
        self._active = False

    def rollback(self) -> None:
        if self._conn is None or not self._active:
            return
        self._conn.rollback()
        self._active = False

    def close(self) -> None:
        if self._conn is None:
            return
        if self._active:
            self.rollback()
        self._conn.close()
        self._conn = None
