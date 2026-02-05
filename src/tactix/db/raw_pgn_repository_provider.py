"""Factory helpers for DuckDB raw PGN repository access."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import duckdb

from tactix._hash_pgn_text import _hash_pgn_text
from tactix.db.duckdb_raw_pgn_repository import (
    DuckDbRawPgnRepository,
    default_raw_pgn_dependencies,
)


def raw_pgn_repository(conn: duckdb.DuckDBPyConnection) -> DuckDbRawPgnRepository:
    """Return a DuckDbRawPgnRepository bound to the provided connection."""
    return DuckDbRawPgnRepository(conn, dependencies=default_raw_pgn_dependencies())


def hash_pgn(pgn: str) -> str:
    """Return the canonical hash for PGN content."""
    return _hash_pgn_text(pgn)


def upsert_raw_pgns(
    conn: duckdb.DuckDBPyConnection,
    rows: Iterable[Mapping[str, object]],
) -> int:
    """Insert raw PGN rows with version tracking."""
    return raw_pgn_repository(conn).upsert_raw_pgns(rows)


def fetch_latest_pgn_hashes(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str],
    source: str | None,
) -> dict[str, str]:
    """Fetch latest PGN hashes for the provided game ids."""
    return raw_pgn_repository(conn).fetch_latest_pgn_hashes(game_ids, source)


def fetch_latest_raw_pgns(
    conn: duckdb.DuckDBPyConnection,
    source: str | None = None,
    limit: int | None = None,
) -> list[dict[str, object]]:
    """Fetch the latest raw PGN rows for a source."""
    return raw_pgn_repository(conn).fetch_latest_raw_pgns(source, limit)


def fetch_raw_pgns_summary(
    conn: duckdb.DuckDBPyConnection,
    *,
    source: str | None = None,
) -> dict[str, object]:
    """Return raw PGN summary payload for the given source."""
    return raw_pgn_repository(conn).fetch_raw_pgns_summary(source=source)
