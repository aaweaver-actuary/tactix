"""Factory helpers for DuckDB tactic repository access."""

from __future__ import annotations

from collections.abc import Mapping

import duckdb

from tactix.db.duckdb_tactic_repository import (
    DuckDbTacticRepository,
    default_tactic_dependencies,
)


def tactic_repository(conn: duckdb.DuckDBPyConnection) -> DuckDbTacticRepository:
    """Return a DuckDbTacticRepository bound to the provided connection."""
    return DuckDbTacticRepository(conn, dependencies=default_tactic_dependencies())


def insert_tactics(
    conn: duckdb.DuckDBPyConnection,
    rows: list[Mapping[str, object]],
) -> list[int]:
    """Insert tactic rows and return ids."""
    return tactic_repository(conn).insert_tactics(rows)


def insert_tactic_outcomes(
    conn: duckdb.DuckDBPyConnection,
    rows: list[Mapping[str, object]],
) -> list[int]:
    """Insert tactic outcome rows and return ids."""
    return tactic_repository(conn).insert_tactic_outcomes(rows)


def upsert_tactic_with_outcome(
    conn: duckdb.DuckDBPyConnection,
    tactic_row: Mapping[str, object],
    outcome_row: Mapping[str, object],
) -> int:
    """Insert a tactic with its outcome and return the tactic id."""
    return tactic_repository(conn).upsert_tactic_with_outcome(tactic_row, outcome_row)


def record_training_attempt(
    conn: duckdb.DuckDBPyConnection,
    payload: Mapping[str, object],
) -> int:
    """Persist a training attempt record."""
    return tactic_repository(conn).record_training_attempt(payload)
