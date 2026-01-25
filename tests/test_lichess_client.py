import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

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

    def test_refreshes_token_on_auth_error(self) -> None:
        class FakeAuthError(Exception):
            def __init__(self, status_code: int) -> None:
                super().__init__("auth failed")
                self.status_code = status_code

        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            lichess_token="old-token",
            lichess_oauth_refresh_token="refresh-token",
            lichess_oauth_client_id="client-id",
            lichess_oauth_client_secret="client-secret",
            use_fixture_when_no_token=False,
        )

        def _refresh_and_set_token(target_settings: Settings) -> str:
            target_settings.lichess_token = "new-token"
            return "new-token"

        with patch("tactix.lichess_client._fetch_remote_games_once") as fetch_once:
            fetch_once.side_effect = [FakeAuthError(401), []]
            with patch(
                "tactix.lichess_client._refresh_lichess_token",
                side_effect=_refresh_and_set_token,
            ) as refresh:
                result = fetch_incremental_games(settings, since_ms=0)

        self.assertEqual(result, [])
        self.assertEqual(fetch_once.call_count, 2)
        refresh.assert_called_once()
        self.assertEqual(settings.lichess_token, "new-token")


if __name__ == "__main__":
    unittest.main()
