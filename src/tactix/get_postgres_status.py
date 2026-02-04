"""Resolve Postgres connectivity status."""

import time

import psycopg2

from tactix._build_schema_label import _build_schema_label
from tactix._collect_tables import _collect_tables
from tactix._connection_kwargs import _connection_kwargs
from tactix.config import Settings
from tactix.init_postgres_schema import init_postgres_schema
from tactix.postgres_enabled import postgres_enabled
from tactix.PostgresStatus import PostgresStatus


def get_postgres_status(settings: Settings) -> PostgresStatus:
    """Return the Postgres status for the provided settings."""
    if not postgres_enabled(settings):
        return PostgresStatus(enabled=False, status="disabled")
    kwargs = _connection_kwargs(settings)
    if not kwargs:
        return PostgresStatus(enabled=False, status="disabled")
    start = time.monotonic()
    try:
        conn = psycopg2.connect(**kwargs)
    except Exception as exc:  # noqa: BLE001
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
