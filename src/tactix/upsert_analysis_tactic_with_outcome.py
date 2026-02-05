"""Upsert tactics and outcome rows into Postgres."""

from collections.abc import Mapping
from typing import cast

from psycopg2.extensions import connection as PgConnection  # noqa: N812

from tactix._delete_existing_analysis import _delete_existing_analysis
from tactix._insert_analysis_outcome import _insert_analysis_outcome
from tactix._insert_analysis_tactic import _insert_analysis_tactic
from tactix.define_base_db_store__db_store import BaseDbStore


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
