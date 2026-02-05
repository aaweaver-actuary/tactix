"""Tactic and practice repository for DuckDB-backed storage."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import duckdb

from tactix.db._rows_to_dicts import _rows_to_dicts
from tactix.db.raw_pgns_queries import latest_raw_pgns_query
from tactix.db.record_training_attempt import record_training_attempt
from tactix.define_base_db_store__db_store import BaseDbStore
from tactix.extract_pgn_metadata import extract_pgn_metadata
from tactix.format_tactics__explanation import format_tactic_explanation
from tactix.sql_tactics import (
    OUTCOME_COLUMNS,
    TACTIC_ANALYSIS_COLUMNS,
    TACTIC_COLUMNS,
    TACTIC_QUEUE_COLUMNS,
)


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


@dataclass(frozen=True)
class PracticeAttemptInputs:
    """Grouped inputs for practice attempt payloads."""

    tactic: Mapping[str, object]
    tactic_id: int
    position_id: int
    attempted_uci: str
    best_uci: str
    correct: bool
    latency_ms: int | None


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
                    best_san,
                    explanation,
                    eval_cp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    next_id,
                    tactic.get("game_id"),
                    tactic.get("position_id"),
                    tactic.get("motif"),
                    tactic.get("severity"),
                    tactic.get("best_uci"),
                    tactic.get("best_san"),
                    tactic.get("explanation"),
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
            """,
            [tactic_id],
        )
        rows = self._dependencies.rows_to_dicts(result)
        return rows[0] if rows else None

    def fetch_practice_queue(
        self,
        limit: int = 20,
        source: str | None = None,
        include_failed_attempt: bool = False,
        exclude_seen: bool = False,
    ) -> list[dict[str, object]]:
        """Return a queue of practice tactics."""
        results = ["missed"]
        if include_failed_attempt:
            results.append("failed_attempt")
        placeholders = ", ".join(["?"] * len(results))
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
        """
        params: list[object] = list(results)
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
        trimmed_attempt = self._normalize_attempted_uci(attempted_uci)
        best_uci = self._normalize_best_uci(tactic)
        correct = bool(best_uci) and trimmed_attempt.lower() == best_uci.lower()
        best_san, explanation = self._resolve_practice_explanation(tactic, best_uci)
        attempt_payload = self._build_practice_attempt_payload(
            PracticeAttemptInputs(
                tactic=tactic,
                tactic_id=tactic_id,
                position_id=position_id,
                attempted_uci=trimmed_attempt,
                best_uci=best_uci,
                correct=correct,
                latency_ms=latency_ms,
            )
        )
        attempt_id = self._dependencies.record_training_attempt(self._conn, attempt_payload)
        message = self._build_practice_message(correct, tactic, best_uci)
        return {
            "attempt_id": attempt_id,
            "tactic_id": tactic_id,
            "position_id": position_id,
            "source": tactic.get("source"),
            "attempted_uci": trimmed_attempt,
            "best_uci": best_uci,
            "correct": correct,
            "success": correct,
            "motif": tactic.get("motif", "unknown"),
            "severity": tactic.get("severity", 0.0),
            "eval_delta": tactic.get("eval_delta", 0) or 0,
            "message": message,
            "best_san": best_san,
            "explanation": explanation,
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
        """
        analysis_params: list[object] = [game_id]
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

    def _normalize_attempted_uci(self, attempted_uci: str) -> str:
        trimmed = attempted_uci.strip()
        if not trimmed:
            raise ValueError("attempted_uci is required")
        return trimmed

    def _normalize_best_uci(self, tactic: Mapping[str, object]) -> str:
        best_uci_raw = tactic.get("best_uci")
        return str(best_uci_raw).strip() if best_uci_raw is not None else ""

    def _resolve_practice_explanation(
        self,
        tactic: Mapping[str, object],
        best_uci: str,
    ) -> tuple[str | None, str | None]:
        fen = self._string_or_none(tactic.get("fen"))
        motif = self._string_or_none(tactic.get("motif"))
        best_san = self._string_or_none(tactic.get("best_san"))
        explanation = self._string_or_none(tactic.get("explanation"))
        generated_san, generated_explanation = self._dependencies.format_tactic_explanation(
            fen,
            best_uci,
            motif,
        )
        return self._resolve_explanation(
            best_san,
            explanation,
            generated_san,
            generated_explanation,
        )

    def _string_or_none(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _resolve_explanation(
        self,
        best_san: str | None,
        explanation: str | None,
        generated_san: str | None,
        generated_explanation: str | None,
    ) -> tuple[str | None, str | None]:
        if not best_san:
            best_san = generated_san or None
        if not explanation:
            explanation = generated_explanation or None
        return best_san, explanation

    def _build_practice_attempt_payload(
        self,
        inputs: PracticeAttemptInputs,
    ) -> dict[str, object]:
        return {
            "tactic_id": inputs.tactic_id,
            "position_id": inputs.position_id,
            "source": inputs.tactic.get("source"),
            "attempted_uci": inputs.attempted_uci,
            "correct": inputs.correct,
            "success": inputs.correct,
            "best_uci": inputs.best_uci,
            "motif": inputs.tactic.get("motif", "unknown"),
            "severity": inputs.tactic.get("severity", 0.0),
            "eval_delta": inputs.tactic.get("eval_delta", 0) or 0,
            "latency_ms": inputs.latency_ms,
        }

    def _build_practice_message(
        self,
        correct: bool,
        tactic: Mapping[str, object],
        best_uci: str,
    ) -> str:
        if correct:
            return f"Correct! {tactic.get('motif', 'tactic')} found."
        return f"Missed it. Best move was {best_uci or '--'}."


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
