"""Persist operational events to Postgres."""

from typing import cast

from psycopg2.extras import Json

from tactix.config import Settings
from tactix.init_postgres_schema import init_postgres_schema
from tactix.legacy_args import apply_legacy_args, apply_legacy_kwargs, init_legacy_values
from tactix.ops_event import OpsEvent
from tactix.postgres_connection import postgres_connection


def _collect_ops_event_values(
    args: tuple[object, ...],
    legacy: dict[str, object],
) -> dict[str, object]:
    ordered_keys = ("component", "event_type", "source", "profile", "metadata")
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
    )


def record_ops_event(
    event: OpsEvent | Settings,
    *args: object,
    **legacy: object,
) -> bool:
    """Insert an ops event into Postgres if available."""
    if isinstance(event, OpsEvent):
        resolved = event
    else:
        values = _collect_ops_event_values(args, legacy)
        resolved = _build_ops_event(event, values)
    with postgres_connection(resolved.settings) as conn:
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
                    resolved.component,
                    resolved.event_type,
                    resolved.source,
                    resolved.profile,
                    Json(resolved.metadata or {}),
                ),
            )
        return True
