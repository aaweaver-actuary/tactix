import tempfile
from pathlib import Path
import unittest

from tactix.config import Settings
from tactix.lichess_client import (
    fetch_incremental_games,
    latest_timestamp,
    read_checkpoint,
    write_checkpoint,
)


class LichessClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
        )

    def test_checkpoint_roundtrip(self) -> None:
        ckpt_path = self.tmp_dir / "since.txt"
        self.assertEqual(read_checkpoint(ckpt_path), 0)
        write_checkpoint(ckpt_path, 1234)
        self.assertEqual(read_checkpoint(ckpt_path), 1234)

    def test_fixture_fetch_respects_since(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            fixture_pgn_path=self.fixture_path,
            use_fixture_when_no_token=True,
        )

        games = fetch_incremental_games(settings, since_ms=0)
        self.assertGreaterEqual(len(games), 2)

        last_ts = latest_timestamp(games)
        self.assertGreater(last_ts, 0)

        newer = fetch_incremental_games(settings, since_ms=last_ts)
        self.assertEqual(newer, [])


if __name__ == "__main__":
    unittest.main()
