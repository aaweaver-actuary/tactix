import json
import logging
from pathlib import Path

import duckdb  # type: ignore
from fastapi.testclient import TestClient

from tactix.api import app

logging.basicConfig(level=logging.WARNING)
logging.getLogger("tactix").setLevel(logging.WARNING)
logging.getLogger("tactix.funclogger").setLevel(logging.WARNING)
logging.getLogger("tactix.trace_context").setLevel(logging.WARNING)

client = TestClient(app)

START_DATE = "2024-06-05"
END_DATE = "2024-06-06"
DB_NAME = "tactix_feature_010_lichess_blitz_mvp"
FIXTURE_NAME = "lichess_blitz_sample.pgn"

headers = {"Authorization": "Bearer local-dev-token"}

pipeline_params = {
    "source": "lichess",
    "profile": "blitz",
    "user_id": "lichess",
    "start_date": START_DATE,
    "end_date": END_DATE,
    "use_fixture": "true",
    "fixture_name": FIXTURE_NAME,
    "db_name": DB_NAME,
    "reset_db": "true",
}

resp = client.post("/api/pipeline/run", params=pipeline_params, headers=headers)
pipeline_payload = resp.json()
print("pipeline_status", resp.status_code)
print("pipeline_response", json.dumps(pipeline_payload, indent=2, sort_keys=True))

summary_params = {
    "source": "lichess",
    "start_date": START_DATE,
    "end_date": END_DATE,
    "db_name": DB_NAME,
}
summary_resp = client.get("/api/dashboard/summary", params=summary_params, headers=headers)
summary_payload = summary_resp.json()
print("summary_status", summary_resp.status_code)
print("summary_response", json.dumps(summary_payload, indent=2, sort_keys=True))

path = Path("data") / f"{DB_NAME}.duckdb"
print("duckdb_path", path)
con = duckdb.connect(str(path))

counts = {}
for table in [
    "games",
    "raw_pgns",
    "positions",
    "user_moves",
    "opportunities",
    "conversions",
    "tactic_outcomes",
    "practice_queue",
]:
    try:
        counts[table] = con.execute(f"select count(*) from {table}").fetchone()[0]
    except Exception as exc:
        counts[table] = f"ERROR: {exc}"
print("table_counts", json.dumps(counts, indent=2, sort_keys=True))

checks = {}
checks["games_null_game_id"] = con.execute(
    "select count(*) from games where game_id is null"
).fetchone()[0]
checks["raw_pgns_null_game_id"] = con.execute(
    "select count(*) from raw_pgns where game_id is null"
).fetchone()[0]
checks["positions_user_to_move"] = con.execute(
    "select count(*) from positions where user_to_move"
).fetchone()[0]
checks["positions_missing_fen"] = con.execute(
    "select count(*) from positions where fen is null or fen = ''"
).fetchone()[0]
checks["user_moves_missing"] = con.execute(
    """
    select count(*)
    from positions p
    left join user_moves m on m.position_id = p.position_id
    where p.user_to_move and m.position_id is null
    """
).fetchone()[0]
checks["user_moves_duplicates"] = con.execute(
    """
    select count(*)
    from (
        select position_id, count(*) as cnt
        from user_moves
        group by position_id
        having count(*) > 1
    )
    """
).fetchone()[0]
checks["conversions_missing_opportunity"] = con.execute(
    """
    select count(*)
    from conversions c
    left join opportunities o on o.opportunity_id = c.opportunity_id
    where o.opportunity_id is null
    """
).fetchone()[0]
checks["tactic_outcomes_missing_tactic"] = con.execute(
    """
    select count(*)
    from tactic_outcomes t
    left join opportunities o on o.opportunity_id = t.tactic_id
    where o.opportunity_id is null
    """
).fetchone()[0]

motif_counts = con.execute(
    "select motif, count(*) from opportunities group by motif order by motif"
).fetchall()
checks["opportunity_motifs"] = {row[0]: row[1] for row in motif_counts}

outcome_counts = con.execute(
    "select result, count(*) from tactic_outcomes group by result order by result"
).fetchall()
checks["outcome_counts"] = {row[0]: row[1] for row in outcome_counts}

print("db_checks", json.dumps(checks, indent=2, sort_keys=True))
con.close()

output = {
    "pipeline_status": resp.status_code,
    "pipeline_response": pipeline_payload,
    "summary_status": summary_resp.status_code,
    "summary_response": summary_payload,
    "table_counts": counts,
    "db_checks": checks,
}
out_path = Path("tmp-logs") / "feature_010_lichess_blitz_output.json"
out_path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
print("wrote_output", out_path)
