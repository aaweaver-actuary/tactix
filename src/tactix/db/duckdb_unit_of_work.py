"""DuckDB unit-of-work implementation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import duckdb

from tactix.db.duckdb_store import get_connection
from tactix.ports.unit_of_work import UnitOfWork


@dataclass
class DuckDbUnitOfWork(UnitOfWork[duckdb.DuckDBPyConnection]):
    """Manage a DuckDB session with explicit transaction boundaries."""

    db_path: Path | str
    connection_factory: Callable[[Path | str], duckdb.DuckDBPyConnection] = get_connection
    _conn: duckdb.DuckDBPyConnection | None = None
    _active: bool = False

    def begin(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = self.connection_factory(self.db_path)
        if not self._active:
            self._conn.execute("BEGIN")
            self._active = True
        return self._conn

    def commit(self) -> None:
        if self._conn is None or not self._active:
            return
        self._conn.execute("COMMIT")
        self._active = False

    def rollback(self) -> None:
        if self._conn is None or not self._active:
            return
        self._conn.execute("ROLLBACK")
        self._active = False

    def close(self) -> None:
        if self._conn is None:
            return
        if self._active:
            self.rollback()
        self._conn.close()
        self._conn = None
