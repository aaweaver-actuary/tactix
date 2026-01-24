import tempfile
from pathlib import Path
import unittest

from tactix.config import Settings
from tactix.chesscom_client import fetch_incremental_games
from tactix.pgn_utils import latest_timestamp


class ChesscomClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_blitz_sample.pgn"
        )

    def test_fixture_fetch_respects_since(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            duckdb_path=self.tmp_dir / "db.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            chesscom_fixture_pgn_path=self.fixture_path,
            chesscom_use_fixture_when_no_token=True,
        )
        settings.apply_source_defaults()

        result = fetch_incremental_games(settings, cursor=None)
        games = result.games
        self.assertGreaterEqual(len(games), 2)

        last_ts = latest_timestamp(games)
        self.assertGreater(last_ts, 0)
        self.assertIsNotNone(result.next_cursor)

        newer = fetch_incremental_games(settings, cursor=result.next_cursor)
        self.assertEqual(newer.games, [])
        self.assertEqual(newer.next_cursor, result.next_cursor)


if __name__ == "__main__":
    unittest.main()
