from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

import time

import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import Json, RealDictCursor

from tactix.config import Settings
from tactix.logging_utils import get_logger

logger = get_logger(__name__)

ANALYSIS_SCHEMA = "tactix_analysis"


@dataclass(slots=True)
class PostgresStatus:
    enabled: bool
    status: str
    latency_ms: float | None = None
    error: str | None = None
    schema: str | None = None
    tables: list[str] | None = None


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
            "CREATE INDEX IF NOT EXISTS ops_events_created_at_idx ON tactix_ops.ops_events (created_at DESC)"
        )


def postgres_analysis_enabled(settings: Settings) -> bool:
    return settings.postgres_analysis_enabled and postgres_enabled(settings)


def init_analysis_schema(conn: PgConnection) -> None:
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {ANALYSIS_SCHEMA}")
        cur.execute(
            f"CREATE SEQUENCE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactics_tactic_id_seq"
        )
        cur.execute(
            f"CREATE SEQUENCE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactic_outcomes_outcome_id_seq"
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactics (
                tactic_id BIGINT PRIMARY KEY DEFAULT nextval('{ANALYSIS_SCHEMA}.tactics_tactic_id_seq'),
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
            f"CREATE INDEX IF NOT EXISTS tactics_position_idx ON {ANALYSIS_SCHEMA}.tactics (position_id)"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS tactics_created_at_idx ON {ANALYSIS_SCHEMA}.tactics (created_at DESC)"
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactic_outcomes (
                outcome_id BIGINT PRIMARY KEY DEFAULT nextval('{ANALYSIS_SCHEMA}.tactic_outcomes_outcome_id_seq'),
                tactic_id BIGINT NOT NULL REFERENCES {ANALYSIS_SCHEMA}.tactics(tactic_id) ON DELETE CASCADE,
                result TEXT,
                user_uci TEXT,
                eval_delta INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS tactic_outcomes_created_at_idx ON {ANALYSIS_SCHEMA}.tactic_outcomes (created_at DESC)"
        )


def upsert_analysis_tactic_with_outcome(
    conn: PgConnection,
    tactic_row: Mapping[str, object],
    outcome_row: Mapping[str, object],
) -> int:
    position_id = tactic_row.get("position_id")
    if position_id is None:
        raise ValueError("position_id is required for Postgres analysis upsert")
    autocommit_state = conn.autocommit
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
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
                    tactic_row.get("game_id"),
                    position_id,
                    tactic_row.get("motif", "unknown"),
                    tactic_row.get("severity", 0.0),
                    tactic_row.get("best_uci", ""),
                    tactic_row.get("best_san"),
                    tactic_row.get("explanation"),
                    tactic_row.get("eval_cp", 0),
                ),
            )
            tactic_id_row = cur.fetchone()
            tactic_id = int(tactic_id_row[0]) if tactic_id_row else 0
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
                    outcome_row.get("result", "unclear"),
                    outcome_row.get("user_uci", ""),
                    outcome_row.get("eval_delta", 0),
                ),
            )
        conn.commit()
        return tactic_id
    except Exception:  # noqa: BLE001
        conn.rollback()
        raise
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
        tables: list[str] = []
        tables.extend(
            [f"tactix_ops.{name}" for name in _list_tables(conn, "tactix_ops")]
        )
        if settings.postgres_analysis_enabled:
            init_analysis_schema(conn)
            tables.extend(
                [
                    f"{ANALYSIS_SCHEMA}.{name}"
                    for name in _list_tables(conn, ANALYSIS_SCHEMA)
                ]
            )
        schema_label = "tactix_ops"
        if settings.postgres_analysis_enabled:
            schema_label = f"tactix_ops,{ANALYSIS_SCHEMA}"
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
