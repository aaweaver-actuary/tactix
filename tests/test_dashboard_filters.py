import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tactix.db.duckdb_store import (
    fetch_metrics,
    fetch_recent_tactics,
    get_connection,
    init_schema,
    insert_positions,
    update_metrics_summary,
    upsert_raw_pgns,
    upsert_tactic_with_outcome,
)
from tactix.pgn_utils import extract_game_id, extract_last_timestamp_ms


class DashboardFilterTests(unittest.TestCase):
    def test_dashboard_filters_by_rating_and_time_control(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        db_path = tmp_dir / "filters.duckdb"
        conn = get_connection(db_path)
        init_schema(conn)

        pgn_one = """
[Event "Filter Game 1"]
[Site "lichess.org/abcd1111"]
[UTCDate "2024.06.01"]
[UTCTime "12:00:00"]
[White "tester"]
[Black "opponent"]
[WhiteElo "1350"]
[TimeControl "600+5"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0
""".strip()
        pgn_two = """
[Event "Filter Game 2"]
[Site "lichess.org/abcd2222"]
[UTCDate "2024.06.02"]
[UTCTime "13:00:00"]
[White "opponent"]
[Black "tester"]
[BlackElo "1850"]
[TimeControl "300"]
[Result "0-1"]

1. d4 d5 2. c4 e6 0-1
""".strip()

        rows = []
        for chunk in (pgn_one, pgn_two):
            rows.append(
                {
                    "game_id": extract_game_id(chunk),
                    "user": "tester",
                    "source": "lichess",
                    "fetched_at": datetime.now(timezone.utc),
                    "pgn": chunk,
                    "last_timestamp_ms": extract_last_timestamp_ms(chunk),
                }
            )
        upsert_raw_pgns(conn, rows)

        positions = []
        for idx, row in enumerate(rows, start=1):
            positions.append(
                {
                    "game_id": row["game_id"],
                    "user": "tester",
                    "source": "lichess",
                    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                    "ply": idx,
                    "move_number": idx,
                    "side_to_move": "w",
                    "uci": "e2e4",
                    "san": "e4",
                    "clock_seconds": 600,
                }
            )
        position_ids = insert_positions(conn, positions)

        for row, position_id in zip(rows, position_ids, strict=False):
            motif = "fork" if row["game_id"].endswith("1111") else "pin"
            upsert_tactic_with_outcome(
                conn,
                {
                    "game_id": row["game_id"],
                    "position_id": position_id,
                    "motif": motif,
                    "severity": 1.0,
                    "best_uci": "e2e4",
                    "eval_cp": 120,
                },
                {"result": "found", "user_uci": "e2e4", "eval_delta": 30},
            )

        update_metrics_summary(conn)

        metrics = fetch_metrics(
            conn,
            source="lichess",
            rating_bucket="1200-1399",
            time_control="600+5",
        )
        self.assertTrue(metrics)
        self.assertTrue(
            all(
                row.get("rating_bucket") == "1200-1399" and row.get("time_control") == "600+5"
                for row in metrics
            )
        )

        tactics = fetch_recent_tactics(
            conn,
            source="lichess",
            motif="fork",
            rating_bucket="1200-1399",
            time_control="600+5",
        )
        self.assertEqual(len(tactics), 1)
        self.assertEqual(tactics[0].get("motif"), "fork")


if __name__ == "__main__":
    unittest.main()
