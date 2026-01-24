import tempfile
from pathlib import Path
import unittest

from tactix.duckdb_store import get_connection, init_schema, upsert_raw_pgns
from tactix.pgn_utils import extract_game_id, split_pgn_chunks


class RawPgnVersioningTests(unittest.TestCase):
    def test_raw_pgn_versioning_and_verbatim_storage(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "tactix.duckdb")
        init_schema(conn)
        fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
        )
        raw_pgn = split_pgn_chunks(fixture_path.read_text())[0]
        game_id = extract_game_id(raw_pgn)

        base_row = {
            "game_id": game_id,
            "user": "lichess",
            "source": "lichess",
            "pgn": raw_pgn,
            "last_timestamp_ms": 1,
        }

        inserted = upsert_raw_pgns(conn, [base_row])
        self.assertEqual(inserted, 1)
        inserted_again = upsert_raw_pgns(conn, [base_row])
        self.assertEqual(inserted_again, 0)

        count = conn.execute(
            "SELECT COUNT(*) FROM raw_pgns WHERE game_id = ?", [game_id]
        ).fetchone()[0]
        self.assertEqual(count, 1)

        stored = conn.execute(
            "SELECT pgn FROM raw_pgns WHERE game_id = ? ORDER BY pgn_version DESC LIMIT 1",
            [game_id],
        ).fetchone()[0]
        self.assertEqual(stored, raw_pgn)

        modified_pgn = raw_pgn + "\n"
        modified_row = {**base_row, "pgn": modified_pgn}
        inserted_modified = upsert_raw_pgns(conn, [modified_row])
        self.assertEqual(inserted_modified, 1)

        versions = conn.execute(
            "SELECT pgn_version FROM raw_pgns WHERE game_id = ? ORDER BY pgn_version",
            [game_id],
        ).fetchall()
        self.assertEqual([row[0] for row in versions], [1, 2])

        latest = conn.execute(
            "SELECT pgn FROM raw_pgns WHERE game_id = ? ORDER BY pgn_version DESC LIMIT 1",
            [game_id],
        ).fetchone()[0]
        self.assertEqual(latest, modified_pgn)
        conn.close()


if __name__ == "__main__":
    unittest.main()
