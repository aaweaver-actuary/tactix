import json
import os
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

import tactix.api as api_module
import tactix.config as config_module
from tactix.db.duckdb_store import get_connection, init_schema


def query_count(conn, sql, params):
    return int(conn.execute(sql, params).fetchone()[0])


def snapshot_state(conn, source, start_date, end_date):
    init_schema(conn)
    counts = {
        "raw_pgns": query_count(
            conn,
            "SELECT COUNT(*) FROM raw_pgns r WHERE r.source = ?",
            (source,),
        ),
        "games": query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM games g
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
        "positions": query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM positions p
            JOIN games g ON g.game_id = p.game_id AND g.source = p.source
            WHERE p.user_to_move IS TRUE
            AND g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
        "user_moves": query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM user_moves u
            JOIN games g ON g.game_id = u.game_id AND g.source = u.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
        "opportunities": query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM opportunities o
            JOIN games g ON g.game_id = o.game_id AND g.source = o.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
        "conversions": query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM conversions c
            JOIN games g ON g.game_id = c.game_id AND g.source = c.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
        "practice_queue": query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM practice_queue q
            JOIN games g ON g.game_id = q.game_id AND g.source = q.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
    }
    game_ids = sorted({
        row[0]
        for row in conn.execute(
            """
            SELECT DISTINCT g.game_id
            FROM games g
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            ORDER BY g.game_id
            """,
            (source, start_date, end_date),
        ).fetchall()
    })
    position_keys = sorted({
        (row[0], int(row[1]))
        for row in conn.execute(
            """
            SELECT p.game_id, p.ply
            FROM positions p
            JOIN games g ON g.game_id = p.game_id AND g.source = p.source
            WHERE p.user_to_move IS TRUE
            AND g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ).fetchall()
    })
    move_keys = sorted({
        int(row[0])
        for row in conn.execute(
            """
            SELECT u.position_id
            FROM user_moves u
            JOIN games g ON g.game_id = u.game_id AND g.source = u.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ).fetchall()
    })
    opportunity_keys = sorted({
        (int(row[0]), row[1], row[2] or "")
        for row in conn.execute(
            """
            SELECT o.position_id, o.motif, o.best_uci
            FROM opportunities o
            JOIN games g ON g.game_id = o.game_id AND g.source = o.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ).fetchall()
    })
    conversion_keys = sorted({
        (int(row[0]), row[1] or "", row[2] or "")
        for row in conn.execute(
            """
            SELECT c.opportunity_id, c.result, c.user_uci
            FROM conversions c
            JOIN games g ON g.game_id = c.game_id AND g.source = c.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ).fetchall()
    })
    practice_keys = sorted({
        (int(row[0]), int(row[1]))
        for row in conn.execute(
            """
            SELECT q.opportunity_id, q.position_id
            FROM practice_queue q
            JOIN games g ON g.game_id = q.game_id AND g.source = q.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ).fetchall()
    })
    raw_pgn_keys = sorted({
        (row[0], row[1] or "", int(row[2] or 0))
        for row in conn.execute(
            "SELECT r.game_id, r.pgn_hash, r.pgn_version FROM raw_pgns r WHERE r.source = ?",
            (source,),
        ).fetchall()
    })
    return {
        "counts": counts,
        "game_ids": game_ids,
        "position_keys": position_keys,
        "move_keys": move_keys,
        "opportunity_keys": opportunity_keys,
        "conversion_keys": conversion_keys,
        "practice_keys": practice_keys,
        "raw_pgn_keys": raw_pgn_keys,
    }


os.environ["TACTIX_API_TOKEN"] = "local-dev-token"
os.environ["TACTIX_DATA_DIR"] = str(Path("/Users/andy/tactix/data"))
os.environ["TACTIX_SOURCE"] = "chesscom"

import importlib
importlib.reload(config_module)
importlib.reload(api_module)

client = TestClient(api_module.app)
params = {
    "source": "chesscom",
    "profile": "bullet",
    "user_id": "groborger",
    "start_date": "2026-02-01",
    "end_date": "2026-02-01",
    "use_fixture": "true",
    "fixture_name": "chesscom_bullet_mate_hanging_2026_02_01.pgn",
    "db_name": "tactix_feature_008_chesscom_bullet_idempotent",
    "reset_db": "true",
}

response_first = client.post(
    "/api/pipeline/run",
    headers={"Authorization": "Bearer local-dev-token"},
    params=params,
)
response_first.raise_for_status()

conn = get_connection(Path("/Users/andy/tactix/data/tactix_feature_008_chesscom_bullet_idempotent.duckdb"))
snapshot_first = snapshot_state(conn, "chesscom", date(2026, 2, 1), date(2026, 2, 1))
conn.close()

params_second = {**params, "reset_db": "false"}
response_second = client.post(
    "/api/pipeline/run",
    headers={"Authorization": "Bearer local-dev-token"},
    params=params_second,
)
response_second.raise_for_status()

conn = get_connection(Path("/Users/andy/tactix/data/tactix_feature_008_chesscom_bullet_idempotent.duckdb"))
snapshot_second = snapshot_state(conn, "chesscom", date(2026, 2, 1), date(2026, 2, 1))
conn.close()

result = {
    "first": snapshot_first,
    "second": snapshot_second,
    "counts_match": snapshot_first["counts"] == snapshot_second["counts"],
    "game_ids_match": snapshot_first["game_ids"] == snapshot_second["game_ids"],
    "position_keys_match": snapshot_first["position_keys"] == snapshot_second["position_keys"],
    "move_keys_match": snapshot_first["move_keys"] == snapshot_second["move_keys"],
    "opportunity_keys_match": snapshot_first["opportunity_keys"] == snapshot_second["opportunity_keys"],
    "conversion_keys_match": snapshot_first["conversion_keys"] == snapshot_second["conversion_keys"],
    "practice_keys_match": snapshot_first["practice_keys"] == snapshot_second["practice_keys"],
    "raw_pgn_keys_match": snapshot_first["raw_pgn_keys"] == snapshot_second["raw_pgn_keys"],
    "positions_equal_user_moves": snapshot_second["counts"]["positions"] == snapshot_second["counts"]["user_moves"],
    "run_id_first": response_first.json().get("run_id"),
    "run_id_second": response_second.json().get("run_id"),
    "fetched_games_first": response_first.json().get("result", {}).get("fetched_games"),
    "fetched_games_second": response_second.json().get("result", {}).get("fetched_games"),
}

output_path = Path("/Users/andy/tactix/tmp-logs/feature_008_chesscom_bullet_idempotent.json")
output_path.write_text(json.dumps(result, indent=2, sort_keys=True))

print(json.dumps({
    "counts_first": snapshot_first["counts"],
    "counts_second": snapshot_second["counts"],
    "matches": {
        "counts": result["counts_match"],
        "game_ids": result["game_ids_match"],
        "position_keys": result["position_keys_match"],
        "move_keys": result["move_keys_match"],
        "opportunity_keys": result["opportunity_keys_match"],
        "conversion_keys": result["conversion_keys_match"],
        "practice_keys": result["practice_keys_match"],
        "raw_pgn_keys": result["raw_pgn_keys_match"],
    },
    "run_ids": [result["run_id_first"], result["run_id_second"]],
}, indent=2))
