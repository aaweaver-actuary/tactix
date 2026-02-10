"""Add practice schedule storage."""

from __future__ import annotations

import duckdb


def _migration_add_practice_schedule(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure practice schedule storage exists."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_schedule (
            tactic_id BIGINT PRIMARY KEY,
            position_id BIGINT,
            game_id TEXT,
            source TEXT,
            motif TEXT,
            result TEXT,
            scheduler TEXT,
            due_at TIMESTAMP,
            interval_days DOUBLE,
            ease DOUBLE,
            state_json TEXT,
            last_reviewed_at TIMESTAMP,
            last_attempt_id BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    columns = {row[1] for row in conn.execute("PRAGMA table_info('practice_schedule')").fetchall()}
    if "last_reviewed_at" not in columns:
        conn.execute("ALTER TABLE practice_schedule ADD COLUMN last_reviewed_at TIMESTAMP")
    if "last_attempt_id" not in columns:
        conn.execute("ALTER TABLE practice_schedule ADD COLUMN last_attempt_id BIGINT")


__all__ = ["_migration_add_practice_schedule"]
