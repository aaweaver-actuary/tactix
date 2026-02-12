"""Tactic and practice repository for DuckDB-backed storage."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import duckdb

from tactix.db._rows_to_dicts import _rows_to_dicts
from tactix.db.raw_pgns_queries import latest_raw_pgns_query
from tactix.db.record_training_attempt import record_training_attempt
from tactix.define_base_db_store__db_store import BaseDbStore
from tactix.domain.practice import PracticeAttemptCandidate, evaluate_practice_attempt
from tactix.domain.spaced_repetition import (
    ScheduleState,
    decode_state_payload,
    encode_state_payload,
    end_of_day,
    get_practice_scheduler,
)
from tactix.extract_pgn_metadata import extract_pgn_metadata
from tactix.format_tactics__explanation import format_tactic_explanation
from tactix.sql_tactics import (
    OUTCOME_COLUMNS,
    TACTIC_ANALYSIS_COLUMNS,
    TACTIC_COLUMNS,
    TACTIC_QUEUE_COLUMNS,
)
from tactix.tactic_scope import allowed_motif_list, is_scoped_motif_row


@dataclass(frozen=True)
class DuckDbTacticDependencies:
    """Dependencies used by the tactic repository."""

    rows_to_dicts: Callable[[duckdb.DuckDBPyRelation], list[dict[str, object]]]
    format_tactic_explanation: Callable[
        [str | None, str, str | None], tuple[str | None, str | None]
    ]
    record_training_attempt: Callable[[duckdb.DuckDBPyConnection, Mapping[str, object]], int]
    extract_pgn_metadata: Callable[[str, str], dict[str, object]]
    require_position_id: Callable[[Mapping[str, object], str], object]
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
                    best_line_uci,
                    tactic_piece,
                    mate_type,
                    best_san,
                    explanation,
                    target_piece,
                    target_square,
                    eval_cp,
                    engine_depth
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    next_id,
                    tactic.get("game_id"),
                    tactic.get("position_id"),
                    tactic.get("motif"),
                    tactic.get("severity"),
                    tactic.get("best_uci"),
                    tactic.get("best_line_uci"),
                    tactic.get("tactic_piece"),
                    tactic.get("mate_type"),
                    tactic.get("best_san"),
                    tactic.get("explanation"),
                    tactic.get("target_piece"),
                    tactic.get("target_square"),
                    tactic.get("eval_cp"),
                    tactic.get("engine_depth"),
                ],
            )
            ids.append(next_id)
        return ids

    def insert_tactic_outcomes(self, rows: list[Mapping[str, object]]) -> list[int]:
        """Insert tactic outcome rows and return ids."""
        if not rows:
            return []
        next_id = self._next_outcome_id()
        ids: list[int] = []
        for outcome in rows:
            next_id = self._insert_tactic_outcome(outcome, next_id)
            ids.append(next_id)
        return ids

    def _next_outcome_id(self) -> int:
        row = self._conn.execute("SELECT MAX(outcome_id) FROM tactic_outcomes").fetchone()
        return int(row[0] or 0) if row else 0

    def _insert_tactic_outcome(self, outcome: Mapping[str, object], next_id: int) -> int:
        outcome_id = next_id + 1
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
                outcome_id,
                outcome.get("tactic_id"),
                outcome.get("result"),
                outcome.get("user_uci"),
                outcome.get("eval_delta"),
            ],
        )
        self._maybe_seed_practice_schedule(outcome)
        return outcome_id

    def _maybe_seed_practice_schedule(self, outcome: Mapping[str, object]) -> None:
        tactic_id = outcome.get("tactic_id")
        result = outcome.get("result")
        if isinstance(tactic_id, int) and isinstance(result, str):
            self._seed_practice_schedule_if_needed(tactic_id, result)

    def upsert_tactic_with_outcome(
        self,
        tactic_row: Mapping[str, object],
        outcome_row: Mapping[str, object],
    ) -> int:
        """Insert a tactic with its outcome and return the tactic id."""
        position_id = self._require_position_id(tactic_row)
        self._delete_existing_for_position_if_needed(position_id, tactic_row.get("game_id"))
        tactic_id = self._insert_single_tactic(tactic_row)
        self._insert_outcome_for_tactic(tactic_id, outcome_row)
        return tactic_id

    def _require_position_id(self, tactic_row: Mapping[str, object]) -> object:
        return self._dependencies.require_position_id(
            tactic_row,
            "position_id is required when inserting tactics",
        )

    def _delete_existing_for_position_if_needed(
        self,
        position_id: object,
        game_id: object | None,
    ) -> None:
        if isinstance(position_id, int):
            game_value = str(game_id) if isinstance(game_id, str) else None
            self._delete_existing_for_position(position_id, game_value)

    def _insert_single_tactic(self, tactic_row: Mapping[str, object]) -> int:
        return self.insert_tactics([tactic_row])[0]

    def _insert_outcome_for_tactic(
        self,
        tactic_id: int,
        outcome_row: Mapping[str, object],
    ) -> None:
        self.insert_tactic_outcomes(
            [
                {
                    **outcome_row,
                    "tactic_id": tactic_id,
                }
            ]
        )

    def _delete_existing_for_position(self, position_id: int, game_id: str | None) -> None:
        params: list[object] = [position_id]
        game_clause = ""
        if game_id:
            game_clause = " AND game_id = ?"
            params.append(game_id)
        self._conn.execute(
            """
            DELETE FROM tactic_outcomes
            WHERE tactic_id IN (
                SELECT tactic_id FROM tactics WHERE position_id = ?
            """
            + game_clause
            + """
            )
            """,
            params,
        )
        self._conn.execute(
            "DELETE FROM tactics WHERE position_id = ?" + game_clause,
            params,
        )

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
            LEFT JOIN positions p ON p.position_id = t.position_id AND p.game_id = t.game_id
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
        self._backfill_practice_schedule(results)
        placeholders = ", ".join(["?"] * len(results))
        motif_placeholders = ", ".join(["?"] * len(allowed))
        now = datetime.now(UTC)
        due_before = end_of_day(now)
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
            FROM practice_schedule s
            INNER JOIN tactics t ON t.tactic_id = s.tactic_id
            INNER JOIN positions p ON p.position_id = s.position_id AND p.game_id = s.game_id
            LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
            WHERE s.result IN ({placeholders})
                AND t.motif IN ({motif_placeholders})
                AND (t.motif != 'mate' OR t.mate_type IS NOT NULL)
                AND COALESCE(t.best_uci, '') != ''
                AND s.due_at <= ?
        """
        params: list[object] = [*results, *allowed, due_before]
        if source:
            query += " AND s.source = ?"
            params.append(source)
        if exclude_seen:
            query += " AND t.tactic_id NOT IN (SELECT tactic_id FROM training_attempts"
            if source:
                query += " WHERE source = ?"
                params.append(source)
            query += ")"
        query += " ORDER BY s.due_at ASC, s.updated_at ASC, t.created_at DESC LIMIT ?"
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
        schedule_update = self._update_practice_schedule_after_attempt(
            tactic_id=tactic_id,
            correct=evaluation.correct,
            attempt_id=attempt_id,
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
            "next_due_at": schedule_update.get("next_due_at"),
            "rescheduled": schedule_update.get("rescheduled"),
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

    def _seed_practice_schedule_if_needed(self, tactic_id: int, result: str) -> None:
        payload = self._resolve_practice_seed_payload(tactic_id, result)
        if not payload:
            return
        self._insert_practice_schedule_row(tactic_id, payload, result)

    def _resolve_practice_seed_payload(
        self,
        tactic_id: int,
        result: str,
    ) -> dict[str, object] | None:
        if not self._should_seed_practice_schedule(result):
            return None
        payload = self._fetch_practice_seed_payload(tactic_id)
        if not payload:
            return None
        if not self._is_scoped_practice_payload(payload):
            return None
        if self._practice_schedule_exists(tactic_id):
            return None
        return payload

    def _should_seed_practice_schedule(self, result: str) -> bool:
        return result in {"missed", "failed_attempt"}

    def _fetch_practice_seed_payload(self, tactic_id: int) -> dict[str, object] | None:
        query_result = self._conn.execute(
            """
            SELECT
                t.tactic_id,
                t.position_id,
                t.game_id,
                t.motif,
                t.mate_type,
                p.source
            FROM tactics t
            INNER JOIN positions p ON p.position_id = t.position_id AND p.game_id = t.game_id
            WHERE t.tactic_id = ?
            """,
            [tactic_id],
        )
        row = query_result.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in query_result.description]
        return dict(zip(columns, row, strict=True))

    def _is_scoped_practice_payload(self, payload: Mapping[str, object]) -> bool:
        motif = payload.get("motif")
        mate_type = payload.get("mate_type")
        motif_value = str(motif) if motif is not None else None
        return is_scoped_motif_row(motif_value, mate_type)

    def _practice_schedule_exists(self, tactic_id: int) -> bool:
        existing = self._conn.execute(
            "SELECT 1 FROM practice_schedule WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        return bool(existing)

    def _insert_practice_schedule_row(
        self,
        tactic_id: int,
        payload: Mapping[str, object],
        result: str,
    ) -> None:
        scheduler = get_practice_scheduler()
        now = datetime.now(UTC)
        schedule_state = scheduler.init_state(now)
        self._conn.execute(
            """
            INSERT INTO practice_schedule (
                tactic_id,
                position_id,
                game_id,
                source,
                motif,
                result,
                scheduler,
                due_at,
                interval_days,
                ease,
                state_json,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            [
                tactic_id,
                payload.get("position_id"),
                payload.get("game_id"),
                payload.get("source"),
                payload.get("motif"),
                result,
                schedule_state.scheduler,
                schedule_state.due_at,
                schedule_state.interval_days,
                schedule_state.ease,
                encode_state_payload(schedule_state.state_payload),
            ],
        )

    def _update_practice_schedule_after_attempt(
        self,
        tactic_id: int,
        correct: bool,
        attempt_id: int,
    ) -> dict[str, object]:
        schedule_row = self._resolve_practice_schedule_row(tactic_id)
        scheduler_name = str(schedule_row.get("scheduler")) if schedule_row else None
        scheduler = get_practice_scheduler(scheduler_name)
        now = datetime.now(UTC)
        state_payload = decode_state_payload(
            schedule_row.get("state_json") if schedule_row else None
        )
        updated = scheduler.review(state_payload, correct, now)
        update = self._build_practice_schedule_update(updated, correct, now, attempt_id)
        if schedule_row:
            self._persist_practice_schedule_update(schedule_row, update)
        return {
            "next_due_at": update["due_at"].isoformat(),
            "rescheduled": update["rescheduled"],
        }

    def _resolve_practice_schedule_row(self, tactic_id: int) -> dict[str, object] | None:
        schedule_row = self._fetch_practice_schedule_row(tactic_id)
        if schedule_row:
            return schedule_row
        result = self._fetch_practice_outcome_result(tactic_id)
        if isinstance(result, str):
            self._seed_practice_schedule_if_needed(tactic_id, result)
        return self._fetch_practice_schedule_row(tactic_id)

    def _fetch_practice_outcome_result(self, tactic_id: int) -> str:
        outcome_row = self._conn.execute(
            "SELECT result FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()
        return outcome_row[0] if outcome_row else "missed"

    def _resolve_practice_due(
        self,
        due_at: datetime,
        correct: bool,
        now: datetime,
    ) -> tuple[datetime, bool]:
        if not correct:
            return end_of_day(now), True
        day_end = end_of_day(now)
        if due_at <= day_end:
            return day_end + timedelta(seconds=1), False
        return due_at, False

    def _build_practice_schedule_update(
        self,
        updated: ScheduleState,
        correct: bool,
        now: datetime,
        attempt_id: int,
    ) -> dict[str, object]:
        due_at, rescheduled = self._resolve_practice_due(updated.due_at, correct, now)
        return {
            "due_at": due_at,
            "rescheduled": rescheduled,
            "interval_days": updated.interval_days,
            "ease": updated.ease,
            "state_json": encode_state_payload(updated.state_payload),
            "last_reviewed_at": now,
            "last_attempt_id": attempt_id,
        }

    def _persist_practice_schedule_update(
        self,
        schedule_row: Mapping[str, object],
        update: Mapping[str, object],
    ) -> None:
        self._conn.execute(
            """
            UPDATE practice_schedule
            SET
                due_at = ?,
                interval_days = ?,
                ease = ?,
                state_json = ?,
                last_reviewed_at = ?,
                last_attempt_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE tactic_id = ?
            """,
            [
                update["due_at"],
                update["interval_days"],
                update["ease"],
                update["state_json"],
                update["last_reviewed_at"],
                update["last_attempt_id"],
                schedule_row.get("tactic_id"),
            ],
        )

    def _fetch_practice_schedule_row(self, tactic_id: int) -> dict[str, object] | None:
        result = self._conn.execute(
            "SELECT * FROM practice_schedule WHERE tactic_id = ?",
            [tactic_id],
        )
        rows = self._dependencies.rows_to_dicts(result)
        return rows[0] if rows else None

    def _backfill_practice_schedule(self, results: list[str]) -> None:
        allowed = allowed_motif_list()
        results_placeholders = ", ".join(["?"] * len(results))
        motif_placeholders = ", ".join(["?"] * len(allowed))
        params: list[object] = [*results, *allowed]
        query = f"""
            SELECT o.tactic_id, o.result
            FROM tactic_outcomes o
            INNER JOIN tactics t ON t.tactic_id = o.tactic_id
            WHERE o.result IN ({results_placeholders})
                AND t.motif IN ({motif_placeholders})
                AND (t.motif != 'mate' OR t.mate_type IS NOT NULL)
                AND t.tactic_id NOT IN (SELECT tactic_id FROM practice_schedule)
        """
        rows = self._conn.execute(query, params).fetchall()
        for tactic_id, result in rows:
            if isinstance(tactic_id, int) and isinstance(result, str):
                self._seed_practice_schedule_if_needed(tactic_id, result)


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
