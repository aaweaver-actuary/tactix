"""Persist training attempts in DuckDB."""

from __future__ import annotations

from collections.abc import Mapping

import duckdb


def record_training_attempt(
    conn: duckdb.DuckDBPyConnection,
    attempt: Mapping[str, object],
) -> int:
    """Insert a training attempt row and return its id."""
    row = conn.execute("SELECT MAX(attempt_id) FROM training_attempts").fetchone()
    next_id = int(row[0] or 0) + 1 if row else 1
    conn.execute(
        """
        INSERT INTO training_attempts (
            attempt_id,
            tactic_id,
            position_id,
            source,
            attempted_uci,
            correct,
            success,
            best_uci,
            motif,
            severity,
            eval_delta,
            latency_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            next_id,
            attempt.get("tactic_id"),
            attempt.get("position_id"),
            attempt.get("source"),
            attempt.get("attempted_uci"),
            attempt.get("correct"),
            attempt.get("success"),
            attempt.get("best_uci"),
            attempt.get("motif"),
            attempt.get("severity"),
            attempt.get("eval_delta"),
            attempt.get("latency_ms"),
        ],
    )
    return next_id
