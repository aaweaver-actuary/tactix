"""Postgres raw PGN repository for persistence and summaries."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import psycopg2
from psycopg2.extensions import connection as PgConnection  # noqa: N812
from psycopg2.extras import RealDictCursor

from tactix._build_pgn_upsert_plan import _build_pgn_upsert_plan
from tactix._has_game_source import _has_game_source
from tactix._parse_game_source import _parse_game_source
from tactix.config import Settings
from tactix.db.raw_pgn_summary import (
    build_raw_pgn_summary_payload,
    coerce_raw_pgn_summary_rows,
)
from tactix.define_db_schemas__const import PGN_SCHEMA
from tactix.init_pgn_schema import init_pgn_schema
from tactix.PgnUpsertPlan import PgnUpsertPlan
from tactix.postgres_connection import postgres_connection
from tactix.postgres_pgns_enabled import postgres_pgns_enabled


@dataclass(frozen=True)
class _RawPgnUpsertContext:
    cur: object
    key: tuple[str, str]
    row: Mapping[str, object]
    latest_meta: tuple[str | None, int]
    latest_cache: dict[tuple[str, str], tuple[str | None, int]]


def _disabled_raw_pgn_summary() -> dict[str, Any]:
    """Return the default disabled raw PGN summary payload."""
    return {
        "status": "disabled",
        "total_rows": 0,
        "distinct_games": 0,
        "latest_ingested_at": None,
        "sources": [],
    }


def _fetch_latest_pgn_metadata(
    cur,
    game_id: str,
    source: str,
) -> tuple[str | None, int]:
    """Return latest PGN hash/version for a game and source."""
    cur.execute(
        f"""
        SELECT pgn_hash, pgn_version
        FROM {PGN_SCHEMA}.raw_pgns
        WHERE game_id = %s AND source = %s
        ORDER BY pgn_version DESC
        LIMIT 1
        """,
        (game_id, source),
    )
    existing = cur.fetchone()
    if existing:
        return existing[0], int(existing[1] or 0)
    return None, 0


def _latest_pgn_metadata(
    cur,
    key: tuple[str, str],
    latest_cache: dict[tuple[str, str], tuple[str | None, int]],
) -> tuple[str | None, int]:
    cached = latest_cache.get(key)
    if cached is not None:
        return cached
    latest_hash, latest_version = _fetch_latest_pgn_metadata(cur, key[0], key[1])
    latest_cache[key] = (latest_hash, latest_version)
    return latest_hash, latest_version


def _insert_raw_pgn_row(
    cur,
    game_id: str,
    source: str,
    row: Mapping[str, object],
    plan: PgnUpsertPlan,
) -> None:
    cur.execute(
        f"""
        INSERT INTO {PGN_SCHEMA}.raw_pgns (
            game_id,
            source,
            player_username,
            fetched_at,
            pgn_raw,
            pgn_normalized,
            pgn_hash,
            pgn_version,
            user_rating,
            time_control,
            ingested_at,
            last_timestamp_ms,
            cursor,
            white_player,
            black_player,
            white_elo,
            black_elo,
            result,
            event,
            site,
            utc_date,
            utc_time,
            termination,
            start_timestamp_ms
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT DO NOTHING
        """,
        (
            game_id,
            source,
            row.get("user"),
            plan.fetched_at,
            plan.pgn_text,
            plan.normalized_pgn,
            plan.pgn_hash,
            plan.pgn_version,
            plan.metadata.get("user_rating"),
            plan.metadata.get("time_control"),
            plan.ingested_at,
            plan.last_timestamp_ms,
            plan.cursor,
            plan.metadata.get("white_player"),
            plan.metadata.get("black_player"),
            plan.metadata.get("white_elo"),
            plan.metadata.get("black_elo"),
            plan.metadata.get("result"),
            plan.metadata.get("event"),
            plan.metadata.get("site"),
            plan.metadata.get("utc_date"),
            plan.metadata.get("utc_time"),
            plan.metadata.get("termination"),
            plan.metadata.get("start_timestamp_ms"),
        ),
    )


def _record_upsert_result(
    cur,
    key: tuple[str, str],
    plan: PgnUpsertPlan,
    latest_cache: dict[tuple[str, str], tuple[str | None, int]],
) -> int:
    """Update the latest cache and return rows affected."""
    if not cur.rowcount:
        return 0
    latest_cache[key] = (plan.pgn_hash, plan.pgn_version)
    return 1


def _apply_pgn_upsert_plan__raw_pgn_row(
    context: _RawPgnUpsertContext,
    plan: PgnUpsertPlan | None,
) -> int:
    """Return the upsert outcome for a plan."""
    if plan is None:
        context.latest_cache[context.key] = context.latest_meta
        return 0
    game_id, source = context.key
    _insert_raw_pgn_row(
        context.cur,
        game_id,
        source,
        context.row,
        plan,
    )
    return _record_upsert_result(
        context.cur,
        context.key,
        plan,
        context.latest_cache,
    )


def _maybe_upsert_raw_pgn_row(
    cur,
    row: Mapping[str, object],
    latest_cache: dict[tuple[str, str], tuple[str | None, int]],
) -> int:
    """Upsert a row if newer metadata is available."""
    game_id, source = _parse_game_source(row)
    if not _has_game_source(game_id, source):
        return 0
    key = (game_id, source)
    latest_hash, latest_version = _latest_pgn_metadata(cur, key, latest_cache)
    plan = _build_pgn_upsert_plan(row, latest_hash, latest_version)
    context = _RawPgnUpsertContext(
        cur=cur,
        key=key,
        row=row,
        latest_meta=(latest_hash, latest_version),
        latest_cache=latest_cache,
    )
    return _apply_pgn_upsert_plan__raw_pgn_row(context, plan)


def _upsert_postgres_raw_pgn_rows(
    cur,
    rows: list[Mapping[str, object]],
) -> int:
    """Upsert rows and return the number inserted."""
    latest_cache: dict[tuple[str, str], tuple[str | None, int]] = {}
    inserted = 0
    for row in rows:
        inserted += _maybe_upsert_raw_pgn_row(cur, row, latest_cache)
    return inserted


def _fetch_raw_pgn_summary(cur) -> tuple[list[Mapping[str, Any]], Mapping[str, Any]]:
    """Return per-source and total raw PGN summary data."""
    cur.execute(
        f"""
        SELECT
            source,
            COUNT(*) AS total_rows,
            COUNT(DISTINCT game_id) AS distinct_games,
            MAX(ingested_at) AS latest_ingested_at
        FROM {PGN_SCHEMA}.raw_pgns
        GROUP BY source
        ORDER BY source
        """
    )
    sources = cur.fetchall()
    cur.execute(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT game_id) AS distinct_games,
            MAX(ingested_at) AS latest_ingested_at
        FROM {PGN_SCHEMA}.raw_pgns
        """
    )
    totals = cur.fetchone() or {}
    return sources, totals if isinstance(totals, Mapping) else {}


class PostgresRawPgnRepository:
    """Encapsulates Postgres-backed raw PGN persistence and reads."""

    def __init__(self, conn: PgConnection) -> None:
        self._conn = conn

    def upsert_raw_pgns(self, rows: Iterable[Mapping[str, object]]) -> int:
        """Insert raw PGN rows inside a transaction."""
        rows_list = list(rows)
        if not rows_list:
            return 0
        autocommit_state = self._conn.autocommit
        self._conn.autocommit = False
        try:
            with self._conn.cursor() as cur:
                inserted = _upsert_postgres_raw_pgn_rows(cur, rows_list)
        except psycopg2.Error:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()
            return inserted
        finally:
            self._conn.autocommit = autocommit_state

    def fetch_latest_pgn_hashes(
        self,
        game_ids: list[str],
        source: str | None,
    ) -> dict[str, str]:
        """Fetch latest PGN hashes for the provided game ids."""
        if not game_ids:
            return {}
        where_parts = ["game_id = ANY(%s)"]
        params: list[object] = [game_ids]
        if source:
            where_parts.append("source = %s")
            params.append(source)
        where_clause = " AND ".join(where_parts)
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT game_id, pgn_hash
                FROM (
                    SELECT
                        game_id,
                        pgn_hash,
                        ROW_NUMBER() OVER (
                            PARTITION BY game_id, source
                            ORDER BY pgn_version DESC
                        ) AS rn
                    FROM {PGN_SCHEMA}.raw_pgns
                    WHERE {where_clause}
                ) AS latest
                WHERE rn = 1
                """,
                params,
            )
            rows = cur.fetchall()
        return {str(game_id): str(pgn_hash) for game_id, pgn_hash in rows if pgn_hash}

    def fetch_latest_raw_pgns(
        self,
        source: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        """Fetch the latest raw PGN rows for a source."""
        params: list[object] = []
        where_clause = ""
        if source:
            where_clause = "WHERE source = %s"
            params.append(source)
        sql = f"""
            SELECT * FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY game_id, source
                        ORDER BY pgn_version DESC
                    ) AS rn
                FROM {PGN_SCHEMA}.raw_pgns
                {where_clause}
            ) AS latest
            WHERE rn = 1
            ORDER BY ingested_at DESC
        """
        if limit is not None:
            sql += " LIMIT %s"
            params.append(limit)
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        for row in rows:
            row.pop("rn", None)
        return rows

    def fetch_raw_pgns_summary(self) -> dict[str, Any]:
        """Return the raw PGN summary payload."""
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            sources, totals = _fetch_raw_pgn_summary(cur)
        return build_raw_pgn_summary_payload(
            sources=coerce_raw_pgn_summary_rows(sources),
            totals=totals,
        )


def fetch_postgres_raw_pgns_summary(settings: Settings) -> dict[str, Any]:
    """Return Postgres raw PGN summary payload."""
    with postgres_connection(settings) as conn:
        return fetch_raw_pgns_summary_with_conn(conn, settings)


def fetch_raw_pgns_summary_with_conn(
    conn: PgConnection | None,
    settings: Settings,
) -> dict[str, Any]:
    """Return raw PGN summary payload using a provided connection."""
    if conn is None or not postgres_pgns_enabled(settings):
        return _disabled_raw_pgn_summary()
    init_pgn_schema(conn)
    repo = PostgresRawPgnRepository(conn)
    return repo.fetch_raw_pgns_summary()
