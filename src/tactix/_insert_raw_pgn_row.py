from collections.abc import Mapping

from tactix.base_db_store import PgnUpsertPlan
from tactix.PGN_SCHEMA import PGN_SCHEMA


def _insert_raw_pgn_row(
    cur,
    game_id: str,
    source: str,
    row: Mapping[str, object],
    plan: PgnUpsertPlan,
) -> None:
    cur.execute(
        f"""
        INSERT INTO {PGN_SCHEMA}.raw_pgns (
            game_id,
            source,
            player_username,
            fetched_at,
            pgn_raw,
            pgn_normalized,
            pgn_hash,
            pgn_version,
            user_rating,
            time_control,
            ingested_at,
            last_timestamp_ms,
            cursor,
            white_player,
            black_player,
            white_elo,
            black_elo,
            result,
            event,
            site,
            utc_date,
            utc_time,
            termination,
            start_timestamp_ms
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT DO NOTHING
        """,
        (
            game_id,
            source,
            row.get("user"),
            plan.fetched_at,
            plan.pgn_text,
            plan.normalized_pgn,
            plan.pgn_hash,
            plan.pgn_version,
            plan.metadata.get("user_rating"),
            plan.metadata.get("time_control"),
            plan.ingested_at,
            plan.last_timestamp_ms,
            plan.cursor,
            plan.metadata.get("white_player"),
            plan.metadata.get("black_player"),
            plan.metadata.get("white_elo"),
            plan.metadata.get("black_elo"),
            plan.metadata.get("result"),
            plan.metadata.get("event"),
            plan.metadata.get("site"),
            plan.metadata.get("utc_date"),
            plan.metadata.get("utc_time"),
            plan.metadata.get("termination"),
            plan.metadata.get("start_timestamp_ms"),
        ),
    )
