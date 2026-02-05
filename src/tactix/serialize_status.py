"""Serialize status models for API responses."""

from typing import Any

from tactix.postgres_status import PostgresStatus


def serialize_status(status: PostgresStatus) -> dict[str, Any]:
    """Return a JSON-serializable payload for the status object."""
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
