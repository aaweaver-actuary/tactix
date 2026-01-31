from __future__ import annotations

import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import Json, RealDictCursor

from tactix.base_db_store import (
    BaseDbStore,
    BaseDbStoreContext,
    OutcomeInsertPlan,
    PgnUpsertPlan,
    TacticInsertPlan,
)
from tactix.config import Settings
from tactix.db.raw_pgn_summary import build_raw_pgn_summary_payload
from tactix.prepare_pgn__chess import normalize_pgn
from tactix.utils.logger import get_logger

logger = get_logger(__name__)

ANALYSIS_SCHEMA = "tactix_analysis"
PGN_SCHEMA = "tactix_pgns"


@dataclass(slots=True)
class PostgresStatus:
    enabled: bool
    status: str
    latency_ms: float | None = None
    error: str | None = None
    schema: str | None = None
    tables: list[str] | None = None


class PostgresStore(BaseDbStore):
    """Postgres-backed store implementation."""

    def __init__(self, context: BaseDbStoreContext) -> None:
        super().__init__(context)

    def get_status(self) -> PostgresStatus:
        return get_postgres_status(self.settings)

    def fetch_ops_events(self, limit: int = 10) -> list[dict[str, Any]]:
        return fetch_ops_events(self.settings, limit=limit)

    def fetch_analysis_tactics(self, limit: int = 10) -> list[dict[str, Any]]:
        return fetch_analysis_tactics(self.settings, limit=limit)

    def fetch_raw_pgns_summary(self) -> dict[str, Any]:
        return fetch_postgres_raw_pgns_summary(self.settings)


def _connection_kwargs(settings: Settings) -> dict[str, Any] | None:
    if settings.postgres_dsn:
        return {"dsn": settings.postgres_dsn}
    if not settings.postgres_host or not settings.postgres_db:
        return None
    return {
        "host": settings.postgres_host,
        "port": settings.postgres_port,
        "dbname": settings.postgres_db,
        "user": settings.postgres_user,
        "password": settings.postgres_password,
        "sslmode": settings.postgres_sslmode,
        "connect_timeout": settings.postgres_connect_timeout_s,
    }


def postgres_enabled(settings: Settings) -> bool:
    return _connection_kwargs(settings) is not None


@contextmanager
def postgres_connection(settings: Settings) -> Iterator[PgConnection | None]:
    kwargs = _connection_kwargs(settings)
    if not kwargs:
        yield None
        return
    conn: PgConnection | None = None
    try:
        conn = psycopg2.connect(**kwargs)
        conn.autocommit = True
    except Exception as exc:  # pragma: no cover - handled by status endpoint
        logger.warning("Postgres connection failed: %s", exc)
        yield None
        return
    try:
        yield conn
    finally:
        if conn is not None:
            conn.close()


def init_postgres_schema(conn: PgConnection) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tactix_ops")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tactix_ops.ops_events (
                id BIGSERIAL PRIMARY KEY,
                component TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT,
                profile TEXT,
                metadata JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ops_events_created_at_idx "
            "ON tactix_ops.ops_events (created_at DESC)"
        )


def postgres_analysis_enabled(settings: Settings) -> bool:
    return settings.postgres_analysis_enabled and postgres_enabled(settings)


def postgres_pgns_enabled(settings: Settings) -> bool:
    return settings.postgres_pgns_enabled and postgres_enabled(settings)


def init_analysis_schema(conn: PgConnection) -> None:
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {ANALYSIS_SCHEMA}")
        cur.execute(f"CREATE SEQUENCE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactics_tactic_id_seq")
        cur.execute(
            f"CREATE SEQUENCE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactic_outcomes_outcome_id_seq"
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactics (
                tactic_id BIGINT PRIMARY KEY
                    DEFAULT nextval('{ANALYSIS_SCHEMA}.tactics_tactic_id_seq'),
                game_id TEXT,
                position_id BIGINT NOT NULL,
                motif TEXT,
                severity DOUBLE PRECISION,
                best_uci TEXT,
                best_san TEXT,
                explanation TEXT,
                eval_cp INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS tactics_position_idx "
            f"ON {ANALYSIS_SCHEMA}.tactics (position_id)"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS tactics_created_at_idx "
            f"ON {ANALYSIS_SCHEMA}.tactics (created_at DESC)"
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactic_outcomes (
                outcome_id BIGINT PRIMARY KEY
                    DEFAULT nextval('{ANALYSIS_SCHEMA}.tactic_outcomes_outcome_id_seq'),
                tactic_id BIGINT NOT NULL
                    REFERENCES {ANALYSIS_SCHEMA}.tactics(tactic_id) ON DELETE CASCADE,
                result TEXT,
                user_uci TEXT,
                eval_delta INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS tactic_outcomes_created_at_idx "
            f"ON {ANALYSIS_SCHEMA}.tactic_outcomes (created_at DESC)"
        )


def init_pgn_schema(conn: PgConnection) -> None:
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {PGN_SCHEMA}")
        cur.execute(f"CREATE SEQUENCE IF NOT EXISTS {PGN_SCHEMA}.raw_pgns_raw_pgn_id_seq")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {PGN_SCHEMA}.raw_pgns (
                raw_pgn_id BIGINT PRIMARY KEY
                    DEFAULT nextval('{PGN_SCHEMA}.raw_pgns_raw_pgn_id_seq'),
                game_id TEXT NOT NULL,
                source TEXT NOT NULL,
                player_username TEXT,
                fetched_at TIMESTAMPTZ,
                pgn_raw TEXT,
                pgn_normalized TEXT,
                pgn_hash TEXT,
                pgn_version INTEGER,
                user_rating INTEGER,
                time_control TEXT,
                ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_timestamp_ms BIGINT,
                cursor TEXT,
                white_player TEXT,
                black_player TEXT,
                white_elo INTEGER,
                black_elo INTEGER,
                result TEXT,
                event TEXT,
                site TEXT,
                utc_date TEXT,
                utc_time TEXT,
                termination TEXT,
                start_timestamp_ms BIGINT
            )
            """
        )
        cur.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS raw_pgns_game_version_uniq
            ON {PGN_SCHEMA}.raw_pgns (game_id, source, pgn_version)
            """
        )
        cur.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS raw_pgns_game_hash_uniq
            ON {PGN_SCHEMA}.raw_pgns (game_id, source, pgn_hash)
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS raw_pgns_source_ts_idx
            ON {PGN_SCHEMA}.raw_pgns (source, last_timestamp_ms DESC)
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS raw_pgns_source_result_idx
            ON {PGN_SCHEMA}.raw_pgns (source, result)
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS raw_pgns_source_time_control_idx
            ON {PGN_SCHEMA}.raw_pgns (source, time_control)
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS raw_pgns_player_idx
            ON {PGN_SCHEMA}.raw_pgns (player_username)
            """
        )


def _hash_pgn_text(pgn: str) -> str:
    return BaseDbStore.hash_pgn(pgn)


def _fetch_latest_pgn_metadata(
    cur,
    game_id: str,
    source: str,
) -> tuple[str | None, int]:
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


def _parse_game_source(row: Mapping[str, object]) -> tuple[str, str]:
    game_id = str(row.get("game_id") or "")
    source = str(row.get("source") or "")
    return game_id, source


def _maybe_upsert_raw_pgn_row(
    cur,
    row: Mapping[str, object],
    latest_cache: dict[tuple[str, str], tuple[str | None, int]],
) -> int:
    game_id, source = _parse_game_source(row)
    if not _has_game_source(game_id, source):
        return 0
    key = (game_id, source)
    latest_hash, latest_version = _latest_pgn_metadata(cur, key, latest_cache)
    plan = _build_pgn_upsert_plan(row, latest_hash, latest_version)
    if plan is None:
        latest_cache[key] = (latest_hash, latest_version)
        return 0
    _insert_raw_pgn_row(cur, game_id, source, row, plan)
    return _record_upsert_result(cur, key, plan, latest_cache)


def _has_game_source(game_id: str, source: str) -> bool:
    return bool(game_id and source)


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


def _build_pgn_upsert_plan(
    row: Mapping[str, object],
    latest_hash: str | None,
    latest_version: int,
) -> PgnUpsertPlan | None:
    pgn_text = str(row.get("pgn") or "")
    return BaseDbStore.build_pgn_upsert_plan(
        pgn_text=pgn_text,
        user=str(row.get("user") or ""),
        latest_hash=latest_hash,
        latest_version=latest_version,
        normalize_pgn=normalize_pgn,
        hash_pgn=_hash_pgn_text,
        fetched_at=cast(datetime | None, row.get("fetched_at")),
        last_timestamp_ms=cast(int, row.get("last_timestamp_ms", 0)),
        cursor=row.get("cursor"),
    )


def _record_upsert_result(
    cur,
    key: tuple[str, str],
    plan: PgnUpsertPlan,
    latest_cache: dict[tuple[str, str], tuple[str | None, int]],
) -> int:
    if not cur.rowcount:
        return 0
    latest_cache[key] = (plan.pgn_hash, plan.pgn_version)
    return 1


def _upsert_postgres_raw_pgn_rows(
    cur,
    rows: list[Mapping[str, object]],
) -> int:
    latest_cache: dict[tuple[str, str], tuple[str | None, int]] = {}
    inserted = 0
    for row in rows:
        inserted += _maybe_upsert_raw_pgn_row(cur, row, latest_cache)
    return inserted


def upsert_postgres_raw_pgns(
    conn: PgConnection,
    rows: list[Mapping[str, object]],
) -> int:
    if not rows:
        return 0
    autocommit_state = conn.autocommit
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            inserted = _upsert_postgres_raw_pgn_rows(cur, rows)
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()
        return inserted
    finally:
        conn.autocommit = autocommit_state


def fetch_postgres_raw_pgns_summary(settings: Settings) -> dict[str, Any]:
    with postgres_connection(settings) as conn:
        if conn is None or not postgres_pgns_enabled(settings):
            return _disabled_raw_pgn_summary()
        init_pgn_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sources, totals = _fetch_raw_pgn_summary(cur)
        return _build_raw_pgn_summary(sources, totals)


def _disabled_raw_pgn_summary() -> dict[str, Any]:
    return {
        "status": "disabled",
        "total_rows": 0,
        "distinct_games": 0,
        "latest_ingested_at": None,
        "sources": [],
    }


def _fetch_raw_pgn_summary(cur) -> tuple[list[Mapping[str, Any]], Mapping[str, Any]]:
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


def _build_raw_pgn_summary(
    sources: list[Mapping[str, Any]], totals: Mapping[str, Any]
) -> dict[str, Any]:
    return build_raw_pgn_summary_payload(sources=sources, totals=totals)


def _delete_existing_analysis(cur, position_id: int) -> None:
    cur.execute(
        f"""
        DELETE FROM {ANALYSIS_SCHEMA}.tactic_outcomes
        WHERE tactic_id IN (
            SELECT tactic_id FROM {ANALYSIS_SCHEMA}.tactics WHERE position_id = %s
        )
        """,
        (position_id,),
    )
    cur.execute(
        f"DELETE FROM {ANALYSIS_SCHEMA}.tactics WHERE position_id = %s",
        (position_id,),
    )


def _insert_analysis_tactic(cur, tactic_plan: TacticInsertPlan) -> int:
    cur.execute(
        f"""
        INSERT INTO {ANALYSIS_SCHEMA}.tactics (
            game_id,
            position_id,
            motif,
            severity,
            best_uci,
            best_san,
            explanation,
            eval_cp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING tactic_id
        """,
        (
            tactic_plan.game_id,
            tactic_plan.position_id,
            tactic_plan.motif,
            tactic_plan.severity,
            tactic_plan.best_uci,
            tactic_plan.best_san,
            tactic_plan.explanation,
            tactic_plan.eval_cp,
        ),
    )
    tactic_id_row = cur.fetchone()
    return int(tactic_id_row[0]) if tactic_id_row else 0


def _insert_analysis_outcome(
    cur,
    tactic_id: int,
    outcome_plan: OutcomeInsertPlan,
) -> None:
    cur.execute(
        f"""
        INSERT INTO {ANALYSIS_SCHEMA}.tactic_outcomes (
            tactic_id,
            result,
            user_uci,
            eval_delta
        )
        VALUES (%s, %s, %s, %s)
        """,
        (
            tactic_id,
            outcome_plan.result,
            outcome_plan.user_uci,
            outcome_plan.eval_delta,
        ),
    )


def upsert_analysis_tactic_with_outcome(
    conn: PgConnection,
    tactic_row: Mapping[str, object],
    outcome_row: Mapping[str, object],
) -> int:
    position_id = cast(
        int,
        BaseDbStore.require_position_id(
            tactic_row,
            "position_id is required for Postgres analysis upsert",
        ),
    )
    tactic_plan = BaseDbStore.build_tactic_insert_plan(
        game_id=tactic_row.get("game_id"),
        position_id=position_id,
        tactic_row=tactic_row,
    )
    outcome_plan = BaseDbStore.build_outcome_insert_plan(outcome_row)
    autocommit_state = conn.autocommit
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            _delete_existing_analysis(cur, position_id)
            tactic_id = _insert_analysis_tactic(cur, tactic_plan)
            _insert_analysis_outcome(cur, tactic_id, outcome_plan)
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()
        return tactic_id
    finally:
        conn.autocommit = autocommit_state


def fetch_analysis_tactics(settings: Settings, limit: int = 10) -> list[dict[str, Any]]:
    with postgres_connection(settings) as conn:
        if conn is None or not postgres_analysis_enabled(settings):
            return []
        init_analysis_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT
                    t.tactic_id,
                    t.game_id,
                    t.position_id,
                    t.motif,
                    t.severity,
                    t.best_uci,
                    t.best_san,
                    t.explanation,
                    t.eval_cp,
                    t.created_at,
                    o.result,
                    o.user_uci,
                    o.eval_delta,
                    o.created_at AS outcome_created_at
                FROM {ANALYSIS_SCHEMA}.tactics t
                LEFT JOIN {ANALYSIS_SCHEMA}.tactic_outcomes o
                    ON o.tactic_id = t.tactic_id
                ORDER BY t.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]


def record_ops_event(
    settings: Settings,
    component: str,
    event_type: str,
    source: str | None = None,
    profile: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    with postgres_connection(settings) as conn:
        if conn is None:
            return False
        init_postgres_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tactix_ops.ops_events
                    (component, event_type, source, profile, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    component,
                    event_type,
                    source,
                    profile,
                    Json(metadata or {}),
                ),
            )
        return True


def fetch_ops_events(settings: Settings, limit: int = 10) -> list[dict[str, Any]]:
    with postgres_connection(settings) as conn:
        if conn is None:
            return []
        init_postgres_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, component, event_type, source, profile, metadata, created_at
                FROM tactix_ops.ops_events
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]


def _list_tables(conn: PgConnection, schema: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
            """,
            (schema,),
        )
        return [row[0] for row in cur.fetchall()]


def _build_schema_label(settings: Settings) -> str:
    schema_label = "tactix_ops"
    if settings.postgres_analysis_enabled:
        schema_label = f"{schema_label},{ANALYSIS_SCHEMA}"
    if settings.postgres_pgns_enabled:
        schema_label = f"{schema_label},{PGN_SCHEMA}"
    return schema_label


def _collect_tables(conn: PgConnection, settings: Settings) -> list[str]:
    tables: list[str] = []
    tables.extend(_schema_tables(conn, "tactix_ops", "tactix_ops"))
    if settings.postgres_analysis_enabled:
        init_analysis_schema(conn)
        tables.extend(_schema_tables(conn, ANALYSIS_SCHEMA, ANALYSIS_SCHEMA))
    if settings.postgres_pgns_enabled:
        init_pgn_schema(conn)
        tables.extend(_schema_tables(conn, PGN_SCHEMA, PGN_SCHEMA))
    return tables


def _schema_tables(conn: PgConnection, schema: str, label: str) -> list[str]:
    return [f"{label}.{name}" for name in _list_tables(conn, schema)]


def get_postgres_status(settings: Settings) -> PostgresStatus:
    if not postgres_enabled(settings):
        return PostgresStatus(enabled=False, status="disabled")
    kwargs = _connection_kwargs(settings)
    if not kwargs:
        return PostgresStatus(enabled=False, status="disabled")
    start = time.monotonic()
    try:
        conn = psycopg2.connect(**kwargs)
    except Exception as exc:
        return PostgresStatus(
            enabled=True,
            status="unreachable",
            error=str(exc),
        )
    latency_ms = (time.monotonic() - start) * 1000
    try:
        conn.autocommit = True
        init_postgres_schema(conn)
        tables = _collect_tables(conn, settings)
        schema_label = _build_schema_label(settings)
        return PostgresStatus(
            enabled=True,
            status="ok",
            latency_ms=round(latency_ms, 2),
            schema=schema_label,
            tables=tables,
        )
    finally:
        conn.close()


def serialize_status(status: PostgresStatus) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "enabled": status.enabled,
        "status": status.status,
    }
    if status.latency_ms is not None:
        payload["latency_ms"] = status.latency_ms
    if status.error:
        payload["error"] = status.error
    if status.schema:
        payload["schema"] = status.schema
    if status.tables is not None:
        payload["tables"] = status.tables
    return payload
