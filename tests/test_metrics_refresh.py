import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tactix.duckdb_store import (
    fetch_metrics,
    get_connection,
    init_schema,
    insert_positions,
    update_metrics_summary,
    upsert_raw_pgns,
    upsert_tactic_with_outcome,
)
from tactix.pgn_utils import extract_game_id, extract_last_timestamp_ms, split_pgn_chunks


class MetricsRefreshTests(unittest.TestCase):
    def test_metrics_refresh_includes_trends_and_breakdowns(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        db_path = tmp_dir / "metrics.duckdb"
        conn = get_connection(db_path)
        init_schema(conn)

        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
        )
        chunks = split_pgn_chunks(fixture_path.read_text())
        rows = []
        for chunk in chunks:
            rows.append(
                {
                    "game_id": extract_game_id(chunk),
                    "user": "lichess",
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
                    "user": "lichess",
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

        for pos, position_id in zip(positions, position_ids, strict=False):
            upsert_tactic_with_outcome(
                conn,
                {
                    "game_id": pos["game_id"],
                    "position_id": position_id,
                    "motif": "discovered_check",
                    "severity": 1.2,
                    "best_uci": "e2e4",
                    "eval_cp": 120,
                },
                {"result": "found", "user_uci": "e2e4", "eval_delta": 30},
            )

        update_metrics_summary(conn)
        metrics = fetch_metrics(conn, source="lichess")

        breakdowns = [m for m in metrics if m.get("metric_type") == "motif_breakdown"]
        trends = [m for m in metrics if m.get("metric_type") == "trend"]
        self.assertTrue(breakdowns)
        self.assertTrue(trends)
        self.assertTrue(any(m.get("window_days") == 7 for m in trends))
        self.assertTrue(any(m.get("window_days") == 30 for m in trends))
        for row in trends:
            self.assertIsNotNone(row.get("trend_date"))
            self.assertIsNotNone(row.get("found_rate"))


if __name__ == "__main__":
    unittest.main()
