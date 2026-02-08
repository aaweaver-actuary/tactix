"""Add latency column to training attempts."""

from __future__ import annotations

import duckdb


def _migration_add_training_attempt_latency(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure training attempts include latency metadata."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('training_attempts')").fetchall()}
    if "latency_ms" not in columns:
        conn.execute("ALTER TABLE training_attempts ADD COLUMN latency_ms BIGINT")
