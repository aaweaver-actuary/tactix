import tempfile
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import chess.pgn

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

    def test_fetch_remote_games_uses_username(self) -> None:
        settings = Settings(
            user="envuser",
            source="lichess",
            duckdb_path=self.tmp_dir / "db.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            lichess_token="token",
            use_fixture_when_no_token=False,
        )

        pgn = (
            "[Event \"Fixture\"]\n"
            "[Site \"https://lichess.org/abcd1234\"]\n"
            "[UTCDate \"2024.06.01\"]\n"
            "[UTCTime \"12:00:00\"]\n"
            "[White \"envuser\"]\n"
            "[Black \"opponent\"]\n"
            "[Result \"1-0\"]\n\n"
            "1. e4 e5 1-0\n"
        )

        games_api = MagicMock()
        games_api.export_by_player.return_value = [pgn]
        fake_client = MagicMock()
        fake_client.games = games_api

        with patch("tactix.lichess_client.build_client", return_value=fake_client):
            from tactix import lichess_client

            result = lichess_client._fetch_remote_games_once(settings, since_ms=0)

        self.assertEqual(len(result), 1)
        games_api.export_by_player.assert_called_once()
        called_user = games_api.export_by_player.call_args[0][0]
        self.assertEqual(called_user, "envuser")

    def test_fixture_games_include_user_as_white_or_black(self) -> None:
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
        self.assertGreater(len(games), 0)
        for row in games:
            game = chess.pgn.read_game(StringIO(row["pgn"]))
            self.assertIsNotNone(game)
            headers = game.headers
            white = headers.get("White", "").lower()
            black = headers.get("Black", "").lower()
            self.assertIn("lichess", {white, black})


if __name__ == "__main__":
    unittest.main()
