from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

import time

import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import Json, RealDictCursor

from tactix.config import Settings
from tactix.logging_utils import get_logger

logger = get_logger(__name__)


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
        yield conn
    except Exception as exc:  # pragma: no cover - handled by status endpoint
        logger.warning("Postgres connection failed: %s", exc)
        yield None
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


def _list_tables(conn: PgConnection) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'tactix_ops'
            ORDER BY table_name
            """
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
        tables = _list_tables(conn)
        return PostgresStatus(
            enabled=True,
            status="ok",
            latency_ms=round(latency_ms, 2),
            schema="tactix_ops",
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
