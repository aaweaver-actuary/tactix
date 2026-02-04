"""Tests for serialize_status helper."""

from __future__ import annotations

from tactix.postgres_status import PostgresStatus
from tactix.serialize_status import serialize_status


def test_serialize_status_minimal() -> None:
    status = PostgresStatus(enabled=False, status="disabled")
    assert serialize_status(status) == {"enabled": False, "status": "disabled"}


def test_serialize_status_full() -> None:
    status = PostgresStatus(
        enabled=True,
        status="ok",
        latency_ms=12.5,
        error="boom",
        schema="tactix",
        tables=["t1", "t2"],
    )
    assert serialize_status(status) == {
        "enabled": True,
        "status": "ok",
        "latency_ms": 12.5,
        "error": "boom",
        "schema": "tactix",
        "tables": ["t1", "t2"],
    }
