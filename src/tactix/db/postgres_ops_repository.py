"""Postgres repository for ops event reads and writes."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from psycopg2.extras import Json, RealDictCursor

from tactix.config import Settings
from tactix.init_postgres_schema import init_postgres_schema
from tactix.legacy_args import apply_legacy_args, apply_legacy_kwargs, init_legacy_values
from tactix.ops_event import OpsEvent
from tactix.postgres_connection import postgres_connection
from tactix.trace_context import get_op_id, get_run_id


def _collect_ops_event_values(
    args: tuple[object, ...],
    legacy: dict[str, object],
) -> dict[str, object]:
    ordered_keys = ("component", "event_type", "source", "profile", "metadata", "run_id", "op_id")
    values = init_legacy_values(ordered_keys)
    apply_legacy_kwargs(values, ordered_keys, legacy)
    apply_legacy_args(values, ordered_keys, args)
    return values


def _build_ops_event(settings: Settings, values: dict[str, object]) -> OpsEvent:
    if values["component"] is None or values["event_type"] is None:
        raise TypeError("component and event_type are required")
    return OpsEvent(
        settings=settings,
        component=cast(str, values["component"]),
        event_type=cast(str, values["event_type"]),
        source=cast(str | None, values["source"]),
        profile=cast(str | None, values["profile"]),
        metadata=cast(dict[str, object] | None, values["metadata"]),
        run_id=_resolve_run_id(settings, cast(str | None, values["run_id"])),
        op_id=_resolve_op_id(cast(str | None, values["op_id"])),
    )


def _resolve_run_id(settings: Settings, value: str | None) -> str | None:
    if value:
        return value
    if settings.run_id:
        return settings.run_id
    return get_run_id()


def _resolve_op_id(value: str | None) -> str | None:
    if value:
        return value
    return get_op_id()


def _resolve_ops_event(
    event: OpsEvent | Settings,
    args: tuple[object, ...],
    legacy: dict[str, object],
) -> OpsEvent:
    if isinstance(event, OpsEvent):
        return event
    values = _collect_ops_event_values(args, legacy)
    return _build_ops_event(event, values)


def _apply_trace_defaults(event: OpsEvent) -> OpsEvent:
    run_id = _resolve_run_id(event.settings, event.run_id)
    op_id = _resolve_op_id(event.op_id)
    if run_id == event.run_id and op_id == event.op_id:
        return event
    return replace(event, run_id=run_id, op_id=op_id)


def record_ops_event(
    event: OpsEvent | Settings,
    *args: object,
    **legacy: object,
) -> bool:
    """Insert an ops event into Postgres if available."""
    resolved = _resolve_ops_event(event, args, legacy)
    resolved = _apply_trace_defaults(resolved)
    with postgres_connection(resolved.settings) as conn:
        if conn is None:
            return False
        init_postgres_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tactix_ops.ops_events
                    (component, event_type, source, profile, metadata, run_id, op_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    resolved.component,
                    resolved.event_type,
                    resolved.source,
                    resolved.profile,
                    Json(resolved.metadata or {}),
                    resolved.run_id,
                    resolved.op_id,
                ),
            )
        return True


def fetch_ops_events(settings: Settings, limit: int = 10) -> list[dict[str, Any]]:
    """Return recent ops events for the given settings."""
    with postgres_connection(settings) as conn:
        if conn is None:
            return []
        return fetch_ops_events_with_conn(conn, limit=limit)


def fetch_ops_events_with_conn(conn, limit: int = 10) -> list[dict[str, Any]]:
    """Return recent ops events for the provided connection."""
    if conn is None:
        return []
    init_postgres_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, component, event_type, source, profile,
                   metadata, run_id, op_id, created_at
            FROM tactix_ops.ops_events
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]
