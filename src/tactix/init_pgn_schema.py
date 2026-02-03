from psycopg2.extensions import connection as PgConnection

from tactix.PGN_SCHEMA import PGN_SCHEMA


def init_pgn_schema(conn: PgConnection) -> None:
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {PGN_SCHEMA}")
        cur.execute(f"CREATE SEQUENCE IF NOT EXISTS {PGN_SCHEMA}.raw_pgns_raw_pgn_id_seq")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {PGN_SCHEMA}.raw_pgns (
                raw_pgn_id BIGINT PRIMARY KEY
                    DEFAULT nextval('{PGN_SCHEMA}.raw_pgns_raw_pgn_id_seq'),
                game_id TEXT NOT NULL,
                source TEXT NOT NULL,
                player_username TEXT,
                fetched_at TIMESTAMPTZ,
                pgn_raw TEXT,
                pgn_normalized TEXT,
                pgn_hash TEXT,
                pgn_version INTEGER,
                user_rating INTEGER,
                time_control TEXT,
                ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_timestamp_ms BIGINT,
                cursor TEXT,
                white_player TEXT,
                black_player TEXT,
                white_elo INTEGER,
                black_elo INTEGER,
                result TEXT,
                event TEXT,
                site TEXT,
                utc_date TEXT,
                utc_time TEXT,
                termination TEXT,
                start_timestamp_ms BIGINT
            )
            """
        )
        cur.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS raw_pgns_game_version_uniq
            ON {PGN_SCHEMA}.raw_pgns (game_id, source, pgn_version)
            """
        )
        cur.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS raw_pgns_game_hash_uniq
            ON {PGN_SCHEMA}.raw_pgns (game_id, source, pgn_hash)
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS raw_pgns_source_ts_idx
            ON {PGN_SCHEMA}.raw_pgns (source, last_timestamp_ms DESC)
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS raw_pgns_source_result_idx
            ON {PGN_SCHEMA}.raw_pgns (source, result)
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS raw_pgns_source_time_control_idx
            ON {PGN_SCHEMA}.raw_pgns (source, time_control)
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS raw_pgns_player_idx
            ON {PGN_SCHEMA}.raw_pgns (player_username)
            """
        )
