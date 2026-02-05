"""Factory helpers for DuckDB tactic repository access."""

from __future__ import annotations

import duckdb

from tactix.db.duckdb_tactic_repository import (
    DuckDbTacticRepository,
    default_tactic_dependencies,
)


def tactic_repository(conn: duckdb.DuckDBPyConnection) -> DuckDbTacticRepository:
    """Return a DuckDbTacticRepository bound to the provided connection."""
    return DuckDbTacticRepository(conn, dependencies=default_tactic_dependencies())
