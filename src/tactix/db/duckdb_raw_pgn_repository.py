"""Raw PGN repository for DuckDB-backed storage."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

import duckdb

from tactix.db._build_raw_pgn_upsert_plan import _build_raw_pgn_upsert_plan
from tactix.db._fetch_next_raw_pgn_id import _fetch_next_raw_pgn_id
from tactix.db._insert_raw_pgn_plan import _insert_raw_pgn_plan
from tactix.db._rows_to_dicts import _rows_to_dicts
from tactix.db.fetch_latest_raw_pgns import fetch_latest_raw_pgns as _fetch_latest_raw_pgns
from tactix.db.raw_pgn_summary import (
    build_raw_pgn_summary_payload,
    coerce_raw_pgn_summary_rows,
)
from tactix.db.raw_pgns_queries import latest_raw_pgns_query
from tactix.db.RawPgnInsertInputs import RawPgnInsertInputs


# pylint: disable=too-many-instance-attributes
@dataclass(frozen=True)
class DuckDbRawPgnDependencies:
    """Dependencies used by the raw PGN repository."""

    fetch_next_raw_pgn_id: Callable[[duckdb.DuckDBPyConnection], int]
    build_raw_pgn_upsert_plan: Callable[
        [
            duckdb.DuckDBPyConnection,
            Mapping[str, object],
            str,
            str,
            dict[tuple[str, str], tuple[str | None, int]],
        ],
        object,
    ]
    insert_raw_pgn_plan: Callable[[duckdb.DuckDBPyConnection, RawPgnInsertInputs], None]
    fetch_latest_raw_pgns: Callable[
        [duckdb.DuckDBPyConnection, str | None, int | None], list[dict[str, object]]
    ]
    latest_raw_pgns_query: Callable[[str], str]
    rows_to_dicts: Callable[[duckdb.DuckDBPyRelation], list[dict[str, object]]]
    build_raw_pgn_summary_payload: Callable[..., dict[str, object]]
    coerce_raw_pgn_summary_rows: Callable[[Iterable[Mapping[str, object]]], list[dict[str, object]]]


class DuckDbRawPgnRepository:
    """Encapsulates raw PGN persistence and reads for DuckDB."""

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        dependencies: DuckDbRawPgnDependencies,
    ) -> None:
        self._conn = conn
        self._dependencies = dependencies

    def upsert_raw_pgns(self, rows: Iterable[Mapping[str, object]]) -> int:
        """Insert raw PGN rows with version tracking."""
        rows_list = list(rows)
        if not rows_list:
            return 0
        self._conn.execute("BEGIN TRANSACTION")
        try:
            inserted = self._upsert_raw_pgn_rows(rows_list)
            self._conn.execute("COMMIT")
        except duckdb.Error:
            self._conn.execute("ROLLBACK")
            raise
        return inserted

    def _upsert_raw_pgn_rows(
        self,
        rows_list: list[Mapping[str, object]],
    ) -> int:
        deps = self._dependencies
        next_id = deps.fetch_next_raw_pgn_id(self._conn)
        latest_cache: dict[tuple[str, str], tuple[str | None, int]] = {}
        inserted = 0
        for row in rows_list:
            game_id = str(row["game_id"])
            source = str(row["source"])
            plan = deps.build_raw_pgn_upsert_plan(
                self._conn,
                row,
                game_id,
                source,
                latest_cache,
            )
            if plan is None:
                continue
            next_id += 1
            deps.insert_raw_pgn_plan(
                self._conn,
                RawPgnInsertInputs(
                    raw_pgn_id=next_id,
                    game_id=game_id,
                    source=source,
                    row=row,
                    plan=plan,
                ),
            )
            latest_cache[(game_id, source)] = (plan.pgn_hash, plan.pgn_version)
            inserted += 1
        return inserted

    def fetch_latest_pgn_hashes(
        self,
        game_ids: list[str],
        source: str | None,
    ) -> dict[str, str]:
        """Fetch latest PGN hashes for the provided game ids."""
        if not game_ids:
            return {}
        placeholders = ", ".join(["?"] * len(game_ids))
        params: list[object] = list(game_ids)
        sql = f"""
            WITH latest_pgns AS (
                {self._dependencies.latest_raw_pgns_query(f"WHERE game_id IN ({placeholders})")}
            )
            SELECT game_id, pgn_hash
            FROM latest_pgns
        """
        if source:
            sql += " WHERE source = ?"
            params.append(source)
        rows = self._conn.execute(sql, params).fetchall()
        return {str(game_id): str(pgn_hash) for game_id, pgn_hash in rows if pgn_hash}

    def fetch_latest_raw_pgns(
        self,
        source: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        """Fetch the latest raw PGN rows for a source."""
        return self._dependencies.fetch_latest_raw_pgns(self._conn, source, limit)

    def fetch_raw_pgns_summary(
        self,
        *,
        source: str | None = None,
    ) -> dict[str, object]:
        """Return raw PGN summary payload for the given source."""
        deps = self._dependencies
        where_clause = ""
        params: list[object] = []
        if source:
            where_clause = "WHERE source = ?"
            params.append(source)
        sources_result = self._conn.execute(
            f"""
            SELECT
                source,
                COUNT(*) AS total_rows,
                COUNT(DISTINCT game_id) AS distinct_games,
                MAX(ingested_at) AS latest_ingested_at
            FROM raw_pgns
            {where_clause}
            GROUP BY source
            ORDER BY source
            """,
            params,
        )
        sources = deps.rows_to_dicts(sources_result)
        totals_result = self._conn.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                COUNT(DISTINCT game_id) AS distinct_games,
                MAX(ingested_at) AS latest_ingested_at
            FROM raw_pgns
            {where_clause}
            """,
            params,
        )
        totals_row = totals_result.fetchone()
        totals_dict: dict[str, object] = {}
        if totals_row:
            columns = [desc[0] for desc in totals_result.description]
            totals_dict = dict(zip(columns, totals_row, strict=False))
        return deps.build_raw_pgn_summary_payload(
            sources=deps.coerce_raw_pgn_summary_rows(sources),
            totals=totals_dict,
        )


def default_raw_pgn_dependencies() -> DuckDbRawPgnDependencies:
    """Return default dependency wiring for DuckDB raw PGN operations."""
    return DuckDbRawPgnDependencies(
        fetch_next_raw_pgn_id=_fetch_next_raw_pgn_id,
        build_raw_pgn_upsert_plan=_build_raw_pgn_upsert_plan,
        insert_raw_pgn_plan=_insert_raw_pgn_plan,
        fetch_latest_raw_pgns=_fetch_latest_raw_pgns,
        latest_raw_pgns_query=latest_raw_pgns_query,
        rows_to_dicts=_rows_to_dicts,
        build_raw_pgn_summary_payload=build_raw_pgn_summary_payload,
        coerce_raw_pgn_summary_rows=coerce_raw_pgn_summary_rows,
    )
