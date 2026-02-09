"""Tactic and practice repository for DuckDB-backed storage."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import duckdb

from tactix.db._rows_to_dicts import _rows_to_dicts
from tactix.db.raw_pgns_queries import latest_raw_pgns_query
from tactix.db.record_training_attempt import record_training_attempt
from tactix.define_base_db_store__db_store import BaseDbStore
from tactix.domain.practice import PracticeAttemptCandidate, evaluate_practice_attempt
from tactix.extract_pgn_metadata import extract_pgn_metadata
from tactix.format_tactics__explanation import format_tactic_explanation
from tactix.sql_tactics import (
    OUTCOME_COLUMNS,
    TACTIC_ANALYSIS_COLUMNS,
    TACTIC_COLUMNS,
    TACTIC_QUEUE_COLUMNS,
)
from tactix.tactic_scope import allowed_motif_list


@dataclass(frozen=True)
class DuckDbTacticDependencies:
    """Dependencies used by the tactic repository."""

    rows_to_dicts: Callable[[duckdb.DuckDBPyRelation], list[dict[str, object]]]
    format_tactic_explanation: Callable[
        [str | None, str, str | None], tuple[str | None, str | None]
    ]
    record_training_attempt: Callable[[duckdb.DuckDBPyConnection, Mapping[str, object]], int]
    extract_pgn_metadata: Callable[[str, str], dict[str, object]]
    require_position_id: Callable[[Mapping[str, object], str], None]
    latest_raw_pgns_query: Callable[[], str]


class DuckDbTacticRepository:
    """Encapsulates tactic insertion, outcomes, and practice flows for DuckDB."""

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        dependencies: DuckDbTacticDependencies,
    ) -> None:
        self._conn = conn
        self._dependencies = dependencies

    def insert_tactics(self, rows: list[Mapping[str, object]]) -> list[int]:
        """Insert tactic rows and return ids."""
        if not rows:
            return []
        row = self._conn.execute("SELECT MAX(tactic_id) FROM tactics").fetchone()
        next_id = int(row[0] or 0) if row else 0
        ids: list[int] = []
        for tactic in rows:
            next_id += 1
            self._conn.execute(
                """
                INSERT INTO tactics (
                    tactic_id,
                    game_id,
                    position_id,
                    motif,
                    severity,
                    best_uci,
                    tactic_piece,
                    mate_type,
                    best_san,
                    explanation,
                    target_piece,
                    target_square,
                    eval_cp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    next_id,
                    tactic.get("game_id"),
                    tactic.get("position_id"),
                    tactic.get("motif"),
                    tactic.get("severity"),
                    tactic.get("best_uci"),
                    tactic.get("tactic_piece"),
                    tactic.get("mate_type"),
                    tactic.get("best_san"),
                    tactic.get("explanation"),
                    tactic.get("target_piece"),
                    tactic.get("target_square"),
                    tactic.get("eval_cp"),
                ],
            )
            ids.append(next_id)
        return ids

    def insert_tactic_outcomes(self, rows: list[Mapping[str, object]]) -> list[int]:
        """Insert tactic outcome rows and return ids."""
        if not rows:
            return []
        row = self._conn.execute("SELECT MAX(outcome_id) FROM tactic_outcomes").fetchone()
        next_id = int(row[0] or 0) if row else 0
        ids: list[int] = []
        for outcome in rows:
            next_id += 1
            self._conn.execute(
                """
                INSERT INTO tactic_outcomes (
                    outcome_id,
                    tactic_id,
                    result,
                    user_uci,
                    eval_delta
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    next_id,
                    outcome.get("tactic_id"),
                    outcome.get("result"),
                    outcome.get("user_uci"),
                    outcome.get("eval_delta"),
                ],
            )
            ids.append(next_id)
        return ids

    def upsert_tactic_with_outcome(
        self,
        tactic_row: Mapping[str, object],
        outcome_row: Mapping[str, object],
    ) -> int:
        """Insert a tactic with its outcome and return the tactic id."""
        deps = self._dependencies
        deps.require_position_id(
            tactic_row,
            "position_id is required when inserting tactics",
        )
        tactic_ids = self.insert_tactics([tactic_row])
        tactic_id = tactic_ids[0]
        self.insert_tactic_outcomes(
            [
                {
                    **outcome_row,
                    "tactic_id": tactic_id,
                }
            ]
        )
        return tactic_id

    def fetch_practice_tactic(self, tactic_id: int) -> dict[str, object] | None:
        """Fetch a single tactic for practice flows."""
        allowed = allowed_motif_list()
        placeholders = ", ".join(["?"] * len(allowed))
        result = self._conn.execute(
            f"""
            SELECT
                {TACTIC_COLUMNS},
                {OUTCOME_COLUMNS},
                p.source,
                p.fen,
                p.uci AS position_uci,
                p.san,
                p.ply,
                p.move_number,
                p.side_to_move,
                p.clock_seconds
            FROM tactics t
            LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
            LEFT JOIN positions p ON p.position_id = t.position_id
            WHERE t.tactic_id = ?
                AND t.motif IN ({placeholders})
                AND (t.motif != 'mate' OR t.mate_type IS NOT NULL)
            """,
            [tactic_id, *allowed],
        )
        rows = self._dependencies.rows_to_dicts(result)
        return rows[0] if rows else None

    def fetch_practice_queue(  # noqa: PLR0915
        self,
        limit: int = 20,
        source: str | None = None,
        include_failed_attempt: bool = False,
        exclude_seen: bool = False,
    ) -> list[dict[str, object]]:
        """Return a queue of practice tactics."""
        allowed = allowed_motif_list()
        results = ["missed"]
        if include_failed_attempt:
            results.append("failed_attempt")
        placeholders = ", ".join(["?"] * len(results))
        motif_placeholders = ", ".join(["?"] * len(allowed))
        query = f"""
            SELECT
                {TACTIC_QUEUE_COLUMNS},
                {OUTCOME_COLUMNS},
                p.source,
                p.fen,
                p.uci AS position_uci,
                p.san,
                p.ply,
                p.move_number,
                p.side_to_move,
                p.clock_seconds
            FROM tactics t
            INNER JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
            INNER JOIN positions p ON p.position_id = t.position_id
            WHERE o.result IN ({placeholders})
                AND t.motif IN ({motif_placeholders})
                AND (t.motif != 'mate' OR t.mate_type IS NOT NULL)
        """
        params: list[object] = [*results, *allowed]
        if source:
            query += " AND p.source = ?"
            params.append(source)
        if exclude_seen:
            query += " AND t.tactic_id NOT IN (SELECT tactic_id FROM training_attempts"
            if source:
                query += " WHERE source = ?"
                params.append(source)
            query += ")"
        query += " ORDER BY t.created_at DESC LIMIT ?"
        params.append(limit)
        result = self._conn.execute(query, params)
        return self._dependencies.rows_to_dicts(result)

    def grade_practice_attempt(
        self,
        tactic_id: int,
        position_id: int,
        attempted_uci: str,
        latency_ms: int | None = None,
    ) -> dict[str, object]:
        """Grade a practice attempt and persist the result."""
        tactic = self._require_practice_tactic(tactic_id, position_id)
        evaluation = evaluate_practice_attempt(
            PracticeAttemptCandidate(
                tactic=tactic,
                tactic_id=tactic_id,
                position_id=position_id,
                attempted_uci=attempted_uci,
                latency_ms=latency_ms,
            ),
            self._dependencies.format_tactic_explanation,
        )
        attempt_id = self._dependencies.record_training_attempt(
            self._conn,
            evaluation.attempt_payload,
        )
        return {
            "attempt_id": attempt_id,
            "tactic_id": tactic_id,
            "position_id": position_id,
            "source": tactic.get("source"),
            "attempted_uci": evaluation.attempted_uci,
            "best_uci": evaluation.best_uci,
            "correct": evaluation.correct,
            "success": evaluation.correct,
            "motif": tactic.get("motif", "unknown"),
            "severity": tactic.get("severity", 0.0),
            "eval_delta": tactic.get("eval_delta", 0) or 0,
            "message": evaluation.message,
            "best_san": evaluation.best_san,
            "explanation": evaluation.explanation,
            "latency_ms": latency_ms,
        }

    def record_training_attempt(self, payload: Mapping[str, object]) -> int:
        """Persist a training attempt record."""
        return self._dependencies.record_training_attempt(self._conn, payload)

    def fetch_game_detail(
        self,
        game_id: str,
        user: str,
        source: str | None = None,
    ) -> dict[str, object]:
        """Fetch a detailed game payload including analysis rows."""
        row, result = self._fetch_latest_pgn_row(game_id, source)
        if not row:
            return {
                "game_id": game_id,
                "source": source,
                "pgn": None,
                "metadata": {},
                "analysis": [],
            }
        pgn_row = self._row_to_dict(result, row)
        pgn_value = pgn_row.get("pgn")
        pgn = str(pgn_value) if pgn_value is not None else None
        metadata = self._dependencies.extract_pgn_metadata(pgn or "", user)
        analysis_rows = self._fetch_game_analysis_rows(game_id, source)
        return {
            "game_id": game_id,
            "source": pgn_row.get("source") or source,
            "pgn": pgn,
            "metadata": metadata,
            "analysis": analysis_rows,
        }

    def _latest_pgns_query(self) -> str:
        return f"""
            WITH latest_pgns AS (
                {self._dependencies.latest_raw_pgns_query()}
            )
            SELECT *
            FROM latest_pgns
            WHERE game_id = ?
        """

    def _fetch_latest_pgn_row(
        self,
        game_id: str,
        source: str | None,
    ) -> tuple[tuple[object, ...] | None, duckdb.DuckDBPyConnection]:
        query = self._latest_pgns_query()
        params: list[object] = [game_id]
        if source:
            query += " AND source = ?"
            params.append(source)
        result = self._conn.execute(query, params)
        row = result.fetchone()
        if row or not source:
            return row, result
        fallback_result = self._conn.execute(self._latest_pgns_query(), [game_id])
        return fallback_result.fetchone(), fallback_result

    def _fetch_game_analysis_rows(
        self,
        game_id: str,
        source: str | None,
    ) -> list[dict[str, object]]:
        allowed = allowed_motif_list()
        placeholders = ", ".join(["?"] * len(allowed))
        analysis_query = f"""
            SELECT
                {TACTIC_ANALYSIS_COLUMNS},
                {OUTCOME_COLUMNS},
                p.move_number,
                p.ply,
                p.san,
                p.uci,
                p.side_to_move,
                p.fen
            FROM tactics t
            LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
            LEFT JOIN positions p ON p.position_id = t.position_id
            WHERE t.game_id = ?
                AND t.motif IN ({placeholders})
                AND (t.motif != 'mate' OR t.mate_type IS NOT NULL)
        """
        analysis_params: list[object] = [game_id, *allowed]
        if source:
            analysis_query += " AND p.source = ?"
            analysis_params.append(source)
        analysis_query += " ORDER BY p.ply ASC, t.created_at ASC"
        return self._dependencies.rows_to_dicts(self._conn.execute(analysis_query, analysis_params))

    def _row_to_dict(
        self,
        result: duckdb.DuckDBPyConnection | duckdb.DuckDBPyRelation,
        row: tuple[object, ...],
    ) -> dict[str, object]:
        columns = [desc[0] for desc in result.description]
        return dict(zip(columns, row, strict=True))

    def _require_practice_tactic(self, tactic_id: int, position_id: int) -> dict[str, object]:
        tactic = self.fetch_practice_tactic(tactic_id)
        if not tactic or tactic.get("position_id") != position_id:
            raise ValueError("Tactic not found for position")
        return tactic


def default_tactic_dependencies() -> DuckDbTacticDependencies:
    """Return default dependency wiring for DuckDB tactic operations."""
    return DuckDbTacticDependencies(
        rows_to_dicts=_rows_to_dicts,
        format_tactic_explanation=format_tactic_explanation,
        record_training_attempt=record_training_attempt,
        extract_pgn_metadata=extract_pgn_metadata,
        require_position_id=BaseDbStore.require_position_id,
        latest_raw_pgns_query=latest_raw_pgns_query,
    )
