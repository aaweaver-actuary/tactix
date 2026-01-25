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
from tactix.pgn_utils import extract_last_timestamp_ms, split_pgn_chunks


class LichessClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
        )
        self.correspondence_fixture_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "lichess_correspondence_sample.pgn"
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

    def test_fixture_fetch_respects_until(self) -> None:
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
        timestamps = [row["last_timestamp_ms"] for row in games]
        max_ts = max(timestamps)

        filtered = fetch_incremental_games(settings, since_ms=0, until_ms=max_ts)
        self.assertLess(len(filtered), len(games))
        self.assertTrue(all(row["last_timestamp_ms"] < max_ts for row in filtered))

    def test_fixture_fetch_filters_rapid_window(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_rapid.duckdb",
            checkpoint_path=self.tmp_dir / "since_rapid.txt",
            metrics_version_file=self.tmp_dir / "metrics_rapid.txt",
            fixture_pgn_path=self.fixture_path,
            use_fixture_when_no_token=True,
            lichess_profile="rapid",
        )

        games = fetch_incremental_games(settings, since_ms=0)
        self.assertGreaterEqual(len(games), 2)
        timestamps = [
            extract_last_timestamp_ms(chunk)
            for chunk in split_pgn_chunks(self.fixture_path.read_text())
        ]
        min_ts = min(timestamps)
        max_ts = max(timestamps)

        filtered = fetch_incremental_games(
            settings, since_ms=min_ts, until_ms=max_ts + 1
        )

        self.assertGreater(len(filtered), 0)
        self.assertLess(len(filtered), len(games))
        self.assertTrue(
            all(min_ts < row["last_timestamp_ms"] < max_ts + 1 for row in filtered)
        )

    def test_fixture_fetch_filters_blitz_window(self) -> None:
        blitz_fixture = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_blitz_sample.pgn"
        )
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_blitz.duckdb",
            checkpoint_path=self.tmp_dir / "since_blitz.txt",
            metrics_version_file=self.tmp_dir / "metrics_blitz.txt",
            fixture_pgn_path=blitz_fixture,
            use_fixture_when_no_token=True,
            lichess_profile="blitz",
        )

        games = fetch_incremental_games(settings, since_ms=0)
        self.assertGreaterEqual(len(games), 2)
        timestamps = [
            extract_last_timestamp_ms(chunk)
            for chunk in split_pgn_chunks(blitz_fixture.read_text())
        ]
        min_ts = min(timestamps)
        max_ts = max(timestamps)

        filtered = fetch_incremental_games(
            settings, since_ms=min_ts, until_ms=max_ts + 1
        )

        self.assertGreater(len(filtered), 0)
        self.assertLess(len(filtered), len(games))
        self.assertTrue(
            all(min_ts < row["last_timestamp_ms"] < max_ts + 1 for row in filtered)
        )

    def test_fixture_fetch_filters_classical_window(self) -> None:
        classical_fixture = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "lichess_classical_sample.pgn"
        )
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_classical.duckdb",
            checkpoint_path=self.tmp_dir / "since_classical.txt",
            metrics_version_file=self.tmp_dir / "metrics_classical.txt",
            fixture_pgn_path=classical_fixture,
            use_fixture_when_no_token=True,
            lichess_profile="classical",
        )

        games = fetch_incremental_games(settings, since_ms=0)
        self.assertGreaterEqual(len(games), 1)
        timestamps = [
            extract_last_timestamp_ms(chunk)
            for chunk in split_pgn_chunks(classical_fixture.read_text())
        ]
        min_ts = min(timestamps)
        max_ts = max(timestamps)

        filtered = fetch_incremental_games(
            settings, since_ms=min_ts, until_ms=max_ts + 1
        )

        self.assertGreater(len(filtered), 0)
        self.assertLess(len(filtered), len(games))
        self.assertTrue(
            all(min_ts < row["last_timestamp_ms"] < max_ts + 1 for row in filtered)
        )

    def test_fixture_fetch_filters_correspondence_window(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_correspondence.duckdb",
            checkpoint_path=self.tmp_dir / "since_correspondence.txt",
            metrics_version_file=self.tmp_dir / "metrics_correspondence.txt",
            fixture_pgn_path=self.correspondence_fixture_path,
            use_fixture_when_no_token=True,
            lichess_profile="correspondence",
        )

        games = fetch_incremental_games(settings, since_ms=0)
        self.assertGreaterEqual(len(games), 1)
        timestamps = [
            extract_last_timestamp_ms(chunk)
            for chunk in split_pgn_chunks(self.correspondence_fixture_path.read_text())
        ]
        min_ts = min(timestamps)
        max_ts = max(timestamps)

        filtered = fetch_incremental_games(
            settings, since_ms=min_ts, until_ms=max_ts + 1
        )

        self.assertGreater(len(filtered), 0)
        self.assertLess(len(filtered), len(games))
        self.assertTrue(
            all(min_ts < row["last_timestamp_ms"] < max_ts + 1 for row in filtered)
        )

        empty = fetch_incremental_games(settings, since_ms=max_ts, until_ms=max_ts + 1)

        self.assertEqual(len(empty), 0)

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
            '[Event "Fixture"]\n'
            '[Site "https://lichess.org/abcd1234"]\n'
            '[UTCDate "2024.06.01"]\n'
            '[UTCTime "12:00:00"]\n'
            '[White "envuser"]\n'
            '[Black "opponent"]\n'
            '[Result "1-0"]\n\n'
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

    def test_profile_perf_type_passed_to_api(self) -> None:
        settings = Settings(
            user="envuser",
            source="lichess",
            duckdb_path=self.tmp_dir / "db.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            lichess_token="token",
            lichess_profile="bullet",
            use_fixture_when_no_token=False,
        )

        games_api = MagicMock()
        games_api.export_by_player.return_value = []
        fake_client = MagicMock()
        fake_client.games = games_api

        with patch("tactix.lichess_client.build_client", return_value=fake_client):
            from tactix import lichess_client

            lichess_client._fetch_remote_games_once(settings, since_ms=0)

        _, kwargs = games_api.export_by_player.call_args
        self.assertEqual(kwargs.get("perf_type"), "bullet")

    def test_blitz_profile_perf_type_passed_to_api(self) -> None:
        settings = Settings(
            user="envuser",
            source="lichess",
            duckdb_path=self.tmp_dir / "db.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            lichess_token="token",
            lichess_profile="blitz",
            use_fixture_when_no_token=False,
        )

        games_api = MagicMock()
        games_api.export_by_player.return_value = []
        fake_client = MagicMock()
        fake_client.games = games_api

        with patch("tactix.lichess_client.build_client", return_value=fake_client):
            from tactix import lichess_client

            lichess_client._fetch_remote_games_once(settings, since_ms=0)

        _, kwargs = games_api.export_by_player.call_args
        self.assertEqual(kwargs.get("perf_type"), "blitz")

    def test_correspondence_profile_perf_type_passed_to_api(self) -> None:
        settings = Settings(
            user="envuser",
            source="lichess",
            duckdb_path=self.tmp_dir / "db.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            lichess_token="token",
            lichess_profile="correspondence",
            use_fixture_when_no_token=False,
        )

        games_api = MagicMock()
        games_api.export_by_player.return_value = []
        fake_client = MagicMock()
        fake_client.games = games_api

        with patch("tactix.lichess_client.build_client", return_value=fake_client):
            from tactix import lichess_client

            lichess_client._fetch_remote_games_once(settings, since_ms=0)

        _, kwargs = games_api.export_by_player.call_args
        self.assertEqual(kwargs.get("perf_type"), "correspondence")

    def test_fetch_remote_games_passes_until(self) -> None:
        settings = Settings(
            user="envuser",
            source="lichess",
            duckdb_path=self.tmp_dir / "db.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            lichess_token="token",
            use_fixture_when_no_token=False,
        )

        games_api = MagicMock()
        games_api.export_by_player.return_value = []
        fake_client = MagicMock()
        fake_client.games = games_api

        with patch("tactix.lichess_client.build_client", return_value=fake_client):
            from tactix import lichess_client

            lichess_client._fetch_remote_games_once(settings, since_ms=0, until_ms=1234)

        _, kwargs = games_api.export_by_player.call_args
        self.assertEqual(kwargs.get("until"), 1234)

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
