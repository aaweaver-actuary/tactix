import os
import tempfile
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import requests
import chess.pgn

from tactix.config import Settings, get_settings
from tactix.chesscom_client import ARCHIVES_URL, fetch_incremental_games
from tactix.pgn_utils import latest_timestamp, split_pgn_chunks


class ChesscomClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_blitz_sample.pgn"
        )
        self.bullet_fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_bullet_sample.pgn"
        )
        self.rapid_fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "chesscom_rapid_sample.pgn"
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

    def test_env_username_applied_and_load_dotenv_called(self) -> None:
        with (
            patch("tactix.config.load_dotenv") as load_mock,
            patch.dict(os.environ, {"CHESSCOM_USERNAME": "envuser"}),
        ):
            settings = get_settings(source="chesscom")

        load_mock.assert_called()
        self.assertEqual(settings.chesscom_user, "envuser")
        self.assertEqual(settings.user, "envuser")

    def test_env_username_used_in_archive_request(self) -> None:
        with patch.dict(os.environ, {"CHESSCOM_USERNAME": "envuser"}):
            settings = get_settings(source="chesscom")

        settings.chesscom_token = "token"
        settings.chesscom_use_fixture_when_no_token = False
        settings.chesscom_fixture_pgn_path = self.fixture_path
        settings.apply_source_defaults()

        pgn_text = split_pgn_chunks(self.fixture_path.read_text())[0]
        archive_url = ARCHIVES_URL.format(username="envuser")

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
                            "uuid": "12345",
                        }
                    ]
                },
            ),
        ]
        captured_urls: list[str] = []

        def fake_get(url, *_args, **_kwargs):
            captured_urls.append(url)
            return responses.pop(0)

        with patch("tactix.chesscom_client.requests.get", side_effect=fake_get):
            result = fetch_incremental_games(settings, cursor=None)

        self.assertEqual(len(result.games), 1)
        self.assertIn(archive_url, captured_urls)

    def test_remote_fetch_filters_by_bullet_profile(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_token="token",
            chesscom_profile="bullet",
            duckdb_path=self.tmp_dir / "db.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            chesscom_fixture_pgn_path=self.bullet_fixture_path,
            chesscom_use_fixture_when_no_token=False,
        )
        settings.apply_source_defaults()
        settings.apply_chesscom_profile("bullet")

        pgn_text = split_pgn_chunks(self.bullet_fixture_path.read_text())[0]
        archive_url = "https://api.chess.com/pub/player/chesscom/games/2024/07"

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
                            "time_class": "blitz",
                            "pgn": pgn_text,
                            "uuid": "game-blitz",
                        },
                        {
                            "time_class": "bullet",
                            "pgn": pgn_text,
                            "uuid": "game-bullet",
                        },
                    ]
                },
            ),
        ]

        def fake_get(*_args, **_kwargs):
            return responses.pop(0)

        with patch("tactix.chesscom_client.requests.get", side_effect=fake_get):
            result = fetch_incremental_games(settings, cursor=None)

        self.assertEqual(len(result.games), 1)
        self.assertEqual(result.games[0]["game_id"], "game-bullet")

    def test_remote_fetch_filters_by_blitz_profile(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_token="token",
            chesscom_profile="blitz",
            duckdb_path=self.tmp_dir / "db.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            chesscom_fixture_pgn_path=self.fixture_path,
            chesscom_use_fixture_when_no_token=False,
        )
        settings.apply_source_defaults()
        settings.apply_chesscom_profile("blitz")

        pgn_text = split_pgn_chunks(self.fixture_path.read_text())[0]
        archive_url = "https://api.chess.com/pub/player/chesscom/games/2024/07"

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
                            "time_class": "bullet",
                            "pgn": pgn_text,
                            "uuid": "game-bullet",
                        },
                        {
                            "time_class": "blitz",
                            "pgn": pgn_text,
                            "uuid": "game-blitz",
                        },
                    ]
                },
            ),
        ]

        def fake_get(*_args, **_kwargs):
            return responses.pop(0)

        with patch("tactix.chesscom_client.requests.get", side_effect=fake_get):
            result = fetch_incremental_games(settings, cursor=None)

        self.assertEqual(len(result.games), 1)
        self.assertEqual(result.games[0]["game_id"], "game-blitz")

    def test_remote_fetch_filters_by_rapid_profile(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_token="token",
            chesscom_profile="rapid",
            duckdb_path=self.tmp_dir / "db.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            chesscom_fixture_pgn_path=self.rapid_fixture_path,
            chesscom_use_fixture_when_no_token=False,
        )
        settings.apply_source_defaults()
        settings.apply_chesscom_profile("rapid")

        pgn_text = split_pgn_chunks(self.rapid_fixture_path.read_text())[0]
        archive_url = "https://api.chess.com/pub/player/chesscom/games/2024/07"

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
                            "time_class": "blitz",
                            "pgn": pgn_text,
                            "uuid": "game-blitz",
                        },
                        {
                            "time_class": "rapid",
                            "pgn": pgn_text,
                            "uuid": "game-rapid",
                        },
                    ]
                },
            ),
        ]

        def fake_get(*_args, **_kwargs):
            return responses.pop(0)

        with patch("tactix.chesscom_client.requests.get", side_effect=fake_get):
            result = fetch_incremental_games(settings, cursor=None)

        self.assertEqual(len(result.games), 1)
        self.assertEqual(result.games[0]["game_id"], "game-rapid")

    def test_fetched_games_include_user_as_white_or_black(self) -> None:
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
        user_lower = settings.user.lower()

        for game in result.games:
            pgn_text = game.get("pgn", "")
            parsed = chess.pgn.read_game(StringIO(pgn_text))
            self.assertIsNotNone(parsed)
            headers = parsed.headers
            white = headers.get("White", "").lower()
            black = headers.get("Black", "").lower()
            self.assertIn(user_lower, {white, black})

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

    def test_remote_fetch_paginates_over_200_games(self) -> None:
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
        archives_url = ARCHIVES_URL.format(username=settings.user)
        total_pages = 5

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

        def page_payload(page: int) -> dict:
            games = []
            for index in range(50):
                games.append(
                    {
                        "time_class": settings.chesscom_time_class,
                        "pgn": pgn_text,
                        "uuid": f"game-{page}-{index}",
                    }
                )
            return {
                "games": games,
                "page": str(page),
                "total_pages": str(total_pages),
            }

        def fake_get(url, *_args, **_kwargs):
            if url == archives_url:
                return DummyResponse(200, json_data={"archives": [archive_url]})

            parsed = urlparse(url)
            if parsed.path.endswith("/games/2024/01"):
                page_value = parse_qs(parsed.query).get("page", ["1"])[0]
                return DummyResponse(200, json_data=page_payload(int(page_value)))

            raise AssertionError(f"Unexpected URL: {url}")

        with patch("tactix.chesscom_client.requests.get", side_effect=fake_get):
            result = fetch_incremental_games(settings, cursor=None)

        self.assertEqual(len(result.games), total_pages * 50)


if __name__ == "__main__":
    unittest.main()
