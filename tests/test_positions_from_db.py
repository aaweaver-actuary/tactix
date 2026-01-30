import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tactix.config import Settings
from tactix.db.duckdb_store import (
    fetch_positions_for_games,
    get_connection,
    init_schema,
    upsert_raw_pgns,
)
from tactix.pgn_utils import (
    extract_game_id,
    extract_last_timestamp_ms,
    split_pgn_chunks,
)
from tactix.pipeline import convert_raw_pgns_to_positions


class PositionsFromDbTests(unittest.TestCase):
    def test_convert_raw_pgns_to_positions_persists_fens(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        db_path = tmp_dir / "positions.duckdb"
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

        settings = Settings(duckdb_path=db_path)
        settings.source = "lichess"
        settings.user = "lichess"
        settings.lichess_user = "lichess"
        settings.rapid_perf = ""
        settings.lichess_profile = ""

        result = convert_raw_pgns_to_positions(settings=settings, source="lichess")
        self.assertGreater(result["positions"], 0)

        game_ids = [row["game_id"] for row in rows]
        positions = fetch_positions_for_games(conn, game_ids)
        self.assertGreater(len(positions), 0)

        sample = positions[0]
        self.assertTrue(sample.get("fen"))
        self.assertIsNotNone(sample.get("ply"))
        self.assertIsNotNone(sample.get("move_number"))
        self.assertIn(sample.get("side_to_move"), {"white", "black"})
        self.assertTrue(sample.get("uci"))
        self.assertTrue(sample.get("san"))
        self.assertIsNotNone(sample.get("clock_seconds"))
        self.assertIn(sample.get("source"), {"lichess"})
        self.assertIn(sample.get("user"), {"lichess"})


if __name__ == "__main__":
    unittest.main()
