import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import requests

from tactix.config import Settings
from tactix.chesscom_client import fetch_incremental_games
from tactix.pgn_utils import latest_timestamp, split_pgn_chunks


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

    def test_remote_fetch_retries_on_429_with_retry_after(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_token="token",
            duckdb_path=self.tmp_dir / "db.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            chesscom_fixture_pgn_path=self.fixture_path,
            chesscom_use_fixture_when_no_token=False,
            chesscom_max_retries=2,
            chesscom_retry_backoff_ms=500,
        )
        settings.apply_source_defaults()

        pgn_text = split_pgn_chunks(self.fixture_path.read_text())[0]
        archive_url = "https://api.chess.com/pub/player/chesscom/games/2024/01"

        class DummyResponse:
            def __init__(self, status_code, json_data=None, headers=None):
                self.status_code = status_code
                self._json = json_data or {}
                self.headers = headers or {}

            def json(self):
                return self._json

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests.HTTPError(f"{self.status_code} Error")

        responses = [
            DummyResponse(429, headers={"Retry-After": "2"}),
            DummyResponse(200, json_data={"archives": [archive_url]}),
            DummyResponse(
                200,
                json_data={
                    "games": [
                        {
                            "time_class": settings.chesscom_time_class,
                            "pgn": pgn_text,
                            "uuid": "12345",
                        }
                    ]
                },
            ),
        ]

        def fake_get(*_args, **_kwargs):
            return responses.pop(0)

        with (
            patch("tactix.chesscom_client.requests.get", side_effect=fake_get),
            patch("tactix.chesscom_client.time.sleep") as sleep_mock,
        ):
            result = fetch_incremental_games(settings, cursor=None)

        self.assertEqual(len(result.games), 1)
        sleep_mock.assert_called_once_with(2.0)

    def test_remote_fetch_paginates_archives(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_token="token",
            duckdb_path=self.tmp_dir / "db.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            chesscom_fixture_pgn_path=self.fixture_path,
            chesscom_use_fixture_when_no_token=False,
        )
        settings.apply_source_defaults()

        pgn_text = split_pgn_chunks(self.fixture_path.read_text())[0]
        archive_url = "https://api.chess.com/pub/player/chesscom/games/2024/01"
        page_two_url = f"{archive_url}?page=2"

        class DummyResponse:
            def __init__(self, status_code, json_data=None, headers=None):
                self.status_code = status_code
                self._json = json_data or {}
                self.headers = headers or {}

            def json(self):
                return self._json

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests.HTTPError(f"{self.status_code} Error")

        responses = [
            DummyResponse(200, json_data={"archives": [archive_url]}),
            DummyResponse(
                200,
                json_data={
                    "games": [
                        {
                            "time_class": settings.chesscom_time_class,
                            "pgn": pgn_text,
                            "uuid": "game-1",
                        }
                    ],
                    "next_page": page_two_url,
                },
            ),
            DummyResponse(
                200,
                json_data={
                    "games": [
                        {
                            "time_class": settings.chesscom_time_class,
                            "pgn": pgn_text,
                            "uuid": "game-2",
                        }
                    ]
                },
            ),
        ]

        def fake_get(*_args, **_kwargs):
            return responses.pop(0)

        with patch("tactix.chesscom_client.requests.get", side_effect=fake_get):
            result = fetch_incremental_games(settings, cursor=None)

        self.assertEqual(len(result.games), 2)


if __name__ == "__main__":
    unittest.main()
