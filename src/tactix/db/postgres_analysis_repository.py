"""Postgres repository for analysis tactics and outcomes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from psycopg2.extensions import connection as PgConnection  # noqa: N812
from psycopg2.extras import RealDictCursor

from tactix.config import Settings
from tactix.define_base_db_store__db_store import BaseDbStore
from tactix.define_db_schemas__const import ANALYSIS_SCHEMA
from tactix.define_outcome_insert_plan__db_store import OutcomeInsertPlan
from tactix.define_tactic_insert_plan__db_store import TacticInsertPlan
from tactix.init_analysis_schema import init_analysis_schema
from tactix.postgres_analysis_enabled import postgres_analysis_enabled
from tactix.postgres_connection import postgres_connection
from tactix.tactic_scope import allowed_motif_list


def fetch_analysis_tactics(settings: Settings, limit: int = 10) -> list[dict[str, Any]]:
    """Return recent tactics for the given settings."""
    with postgres_connection(settings) as conn:
        return fetch_analysis_tactics_with_conn(conn, settings, limit=limit)


def fetch_analysis_tactics_with_conn(
    conn: PgConnection | None,
    settings: Settings,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return recent tactics using a provided connection."""
    if conn is None or not postgres_analysis_enabled(settings):
        return []
    init_analysis_schema(conn)
    allowed = allowed_motif_list()
    placeholders = ", ".join(["%s"] * len(allowed))
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT
                t.tactic_id,
                t.game_id,
                t.position_id,
                t.motif,
                t.severity,
                t.best_uci,
                t.best_line_uci,
                t.tactic_piece,
                t.mate_type,
                t.best_san,
                t.explanation,
                t.target_piece,
                t.target_square,
                t.eval_cp,
                t.engine_depth,
                t.created_at,
                o.result,
                o.user_uci,
                o.eval_delta,
                o.created_at AS outcome_created_at
            FROM {ANALYSIS_SCHEMA}.tactics t
            LEFT JOIN {ANALYSIS_SCHEMA}.tactic_outcomes o
                ON o.tactic_id = t.tactic_id
            WHERE t.motif IN ({placeholders})
                AND (t.motif != 'mate' OR t.mate_type IS NOT NULL)
            ORDER BY t.created_at DESC
            LIMIT %s
            """,
            (*allowed, limit),
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def _delete_existing_analysis(cur, position_id: int) -> None:
    """Delete existing tactics and outcomes for a position id."""
    cur.execute(
        f"""
        DELETE FROM {ANALYSIS_SCHEMA}.tactic_outcomes
        WHERE tactic_id IN (
            SELECT tactic_id FROM {ANALYSIS_SCHEMA}.tactics WHERE position_id = %s
        )
        """,
        (position_id,),
    )
    cur.execute(
        f"DELETE FROM {ANALYSIS_SCHEMA}.tactics WHERE position_id = %s",
        (position_id,),
    )


def _insert_analysis_tactic(cur, tactic_plan: TacticInsertPlan) -> int:
    """Insert a tactic row and return its id."""
    cur.execute(
        f"""
        INSERT INTO {ANALYSIS_SCHEMA}.tactics (
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
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING tactic_id
        """,
        (
            tactic_plan.game_id,
            tactic_plan.position_id,
            tactic_plan.motif,
            tactic_plan.severity,
            tactic_plan.best_uci,
            tactic_plan.best_line_uci,
            tactic_plan.tactic_piece,
            tactic_plan.mate_type,
            tactic_plan.best_san,
            tactic_plan.explanation,
            tactic_plan.target_piece,
            tactic_plan.target_square,
            tactic_plan.eval_cp,
            tactic_plan.engine_depth,
        ),
    )
    tactic_id_row = cur.fetchone()
    return int(tactic_id_row[0]) if tactic_id_row else 0


def _insert_analysis_outcome(
    cur,
    tactic_id: int,
    outcome_plan: OutcomeInsertPlan,
) -> None:
    """Insert an analysis outcome row for a tactic."""
    cur.execute(
        f"""
        INSERT INTO {ANALYSIS_SCHEMA}.tactic_outcomes (
            tactic_id,
            result,
            user_uci,
            eval_delta
        )
        VALUES (%s, %s, %s, %s)
        """,
        (
            tactic_id,
            outcome_plan.result,
            outcome_plan.user_uci,
            outcome_plan.eval_delta,
        ),
    )


def upsert_analysis_tactic_with_outcome(
    conn: PgConnection,
    tactic_row: Mapping[str, object],
    outcome_row: Mapping[str, object],
) -> int:
    """Upsert a tactic and its outcome and return the tactic id."""
    position_id = cast(
        int,
        BaseDbStore.require_position_id(
            tactic_row,
            "position_id is required for Postgres analysis upsert",
        ),
    )
    tactic_plan = BaseDbStore.build_tactic_insert_plan(
        game_id=tactic_row.get("game_id"),
        position_id=position_id,
        tactic_row=tactic_row,
    )
    outcome_plan = BaseDbStore.build_outcome_insert_plan(outcome_row)
    autocommit_state = conn.autocommit
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            _delete_existing_analysis(cur, position_id)
            tactic_id = _insert_analysis_tactic(cur, tactic_plan)
            _insert_analysis_outcome(cur, tactic_id, outcome_plan)
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()
        return tactic_id
    finally:
        conn.autocommit = autocommit_state
