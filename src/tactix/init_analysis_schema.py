"""Initialize analysis schema objects in Postgres."""

from psycopg2.extensions import connection as PgConnection  # noqa: N812

from tactix.define_db_schemas__const import ANALYSIS_SCHEMA


def init_analysis_schema(conn: PgConnection) -> None:
    """Create analysis schema tables and indices if missing."""
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {ANALYSIS_SCHEMA}")
        cur.execute(f"CREATE SEQUENCE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactics_tactic_id_seq")
        cur.execute(
            f"CREATE SEQUENCE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactic_outcomes_outcome_id_seq"
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ANALYSIS_SCHEMA}.positions (
                position_id BIGINT PRIMARY KEY,
                game_id TEXT,
                source TEXT,
                fen TEXT,
                ply INTEGER,
                move_number INTEGER,
                side_to_move TEXT,
                uci TEXT,
                san TEXT,
                clock_seconds DOUBLE PRECISION,
                is_legal BOOLEAN,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS positions_game_idx "
            f"ON {ANALYSIS_SCHEMA}.positions (game_id)"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS positions_created_at_idx "
            f"ON {ANALYSIS_SCHEMA}.positions (created_at DESC)"
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactics (
                tactic_id BIGINT PRIMARY KEY
                    DEFAULT nextval('{ANALYSIS_SCHEMA}.tactics_tactic_id_seq'),
                game_id TEXT,
                position_id BIGINT NOT NULL,
                motif TEXT,
                severity DOUBLE PRECISION,
                best_uci TEXT,
                best_line_uci TEXT,
                tactic_piece TEXT,
                mate_type TEXT,
                best_san TEXT,
                explanation TEXT,
                target_piece TEXT,
                target_square TEXT,
                eval_cp INTEGER,
                engine_depth INTEGER,
                confidence TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"ALTER TABLE {ANALYSIS_SCHEMA}.tactics ADD COLUMN IF NOT EXISTS tactic_piece TEXT"
        )
        cur.execute(
            f"ALTER TABLE {ANALYSIS_SCHEMA}.tactics ADD COLUMN IF NOT EXISTS mate_type TEXT"
        )
        cur.execute(
            f"ALTER TABLE {ANALYSIS_SCHEMA}.tactics ADD COLUMN IF NOT EXISTS best_line_uci TEXT"
        )
        cur.execute(
            f"ALTER TABLE {ANALYSIS_SCHEMA}.tactics ADD COLUMN IF NOT EXISTS target_piece TEXT"
        )
        cur.execute(
            f"ALTER TABLE {ANALYSIS_SCHEMA}.tactics ADD COLUMN IF NOT EXISTS target_square TEXT"
        )
        cur.execute(
            f"ALTER TABLE {ANALYSIS_SCHEMA}.tactics ADD COLUMN IF NOT EXISTS engine_depth INTEGER"
        )
        cur.execute(
            f"ALTER TABLE {ANALYSIS_SCHEMA}.tactics ADD COLUMN IF NOT EXISTS confidence TEXT"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS tactics_position_idx "
            f"ON {ANALYSIS_SCHEMA}.tactics (position_id)"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS tactics_created_at_idx "
            f"ON {ANALYSIS_SCHEMA}.tactics (created_at DESC)"
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ANALYSIS_SCHEMA}.tactic_outcomes (
                outcome_id BIGINT PRIMARY KEY
                    DEFAULT nextval('{ANALYSIS_SCHEMA}.tactic_outcomes_outcome_id_seq'),
                tactic_id BIGINT NOT NULL
                    REFERENCES {ANALYSIS_SCHEMA}.tactics(tactic_id) ON DELETE CASCADE,
                result TEXT,
                user_uci TEXT,
                eval_delta INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS tactic_outcomes_created_at_idx "
            f"ON {ANALYSIS_SCHEMA}.tactic_outcomes (created_at DESC)"
        )
