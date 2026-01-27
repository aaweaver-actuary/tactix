import os
import tempfile
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import requests
import chess.pgn

from tactix.config import Settings, get_settings
from tactix.chesscom_client import (
    ARCHIVES_URL,
    _auth_headers,
    _build_cursor,
    _coerce_int,
    _fetch_archive_pages,
    _fetch_remote_games,
    _filter_by_cursor,
    _get_with_backoff,
    _load_fixture_games,
    _next_page_url,
    _parse_cursor,
    _parse_retry_after,
    fetch_incremental_games,
    read_cursor,
    write_cursor,
)
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
        self.classical_fixture_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "chesscom_classical_sample.pgn"
        )
        self.correspondence_fixture_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "chesscom_correspondence_sample.pgn"
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

    def test_retry_after_parsing(self) -> None:
        self.assertEqual(_parse_retry_after("2.5"), 2.5)
        self.assertEqual(_parse_retry_after("0"), 0.0)
        self.assertIsNone(_parse_retry_after("invalid"))

        future = datetime.now(tz=timezone.utc) + timedelta(seconds=60)
        header = format_datetime(future)
        self.assertIsNotNone(_parse_retry_after(header))

    def test_get_with_backoff_retries_429(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_token="token",
            chesscom_use_fixture_when_no_token=False,
            chesscom_max_retries=1,
            chesscom_retry_backoff_ms=0,
            duckdb_path=self.tmp_dir / "db_backoff.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "since_backoff.txt",
            metrics_version_file=self.tmp_dir / "metrics_backoff.txt",
            chesscom_fixture_pgn_path=self.fixture_path,
        )

        class DummyResponse:
            def __init__(self, status_code, headers=None):
                self.status_code = status_code
                self.headers = headers or {}

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests.HTTPError(f"{self.status_code} Error")

        responses = [
            DummyResponse(429, headers={"Retry-After": "0"}),
            DummyResponse(200),
        ]

        def fake_get(*_args, **_kwargs):
            return responses.pop(0)

        with (
            patch("tactix.chesscom_client.requests.get", side_effect=fake_get),
            patch("tactix.chesscom_client.time.sleep", return_value=None),
        ):
            response = _get_with_backoff(settings, "https://example.com", timeout=5)

        self.assertEqual(response.status_code, 200)

    def test_write_cursor_none_roundtrip(self) -> None:
        path = self.tmp_dir / "cursor.txt"
        write_cursor(path, None)
        self.assertIsNone(read_cursor(path))

    def test_load_fixture_missing_path(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            duckdb_path=self.tmp_dir / "db_missing.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "since_missing.txt",
            metrics_version_file=self.tmp_dir / "metrics_missing.txt",
            chesscom_fixture_pgn_path=self.tmp_dir / "missing.pgn",
            chesscom_use_fixture_when_no_token=True,
        )
        settings.apply_source_defaults()

        games = _load_fixture_games(settings, since_ms=0)
        self.assertEqual(games, [])

    def test_next_page_url_dict_and_coerce_int(self) -> None:
        current = "https://api.chess.com/pub/player/user/games/2024/07"
        data = {"next": {"href": "https://example.com/next"}}
        self.assertEqual(_next_page_url(data, current), "https://example.com/next")
        self.assertIsNone(_coerce_int("bad"))

    def test_fetch_archive_pages_detects_loop(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            duckdb_path=self.tmp_dir / "db_pages.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "since_pages.txt",
            metrics_version_file=self.tmp_dir / "metrics_pages.txt",
            chesscom_fixture_pgn_path=self.fixture_path,
        )

        class DummyResponse:
            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

        def fake_get(*_args, **_kwargs):
            return DummyResponse({"games": [], "next_page": "https://example.com/loop"})

        with patch("tactix.chesscom_client._get_with_backoff", side_effect=fake_get) as backoff:
            games = _fetch_archive_pages(settings, "https://example.com/loop")

        self.assertEqual(games, [])
        self.assertEqual(backoff.call_count, 1)

    def test_fetch_remote_games_fallback_and_no_archives(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            duckdb_path=self.tmp_dir / "db_remote.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "since_remote.txt",
            metrics_version_file=self.tmp_dir / "metrics_remote.txt",
            chesscom_fixture_pgn_path=self.fixture_path,
            chesscom_use_fixture_when_no_token=True,
        )
        settings.apply_source_defaults()

        with patch("tactix.chesscom_client._get_with_backoff", side_effect=RuntimeError("boom")):
            fallback_games = _fetch_remote_games(settings, since_ms=0)
        self.assertGreaterEqual(len(fallback_games), 1)

        class DummyResponse:
            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

        with patch("tactix.chesscom_client._get_with_backoff", return_value=DummyResponse({"archives": []})):
            empty = _fetch_remote_games(settings, since_ms=0)
        self.assertEqual(empty, [])

    def test_cursor_helpers(self) -> None:
        self.assertEqual(_parse_cursor("123:abc"), (123, "abc"))
        self.assertEqual(_parse_cursor("456"), (456, ""))
        self.assertEqual(_parse_cursor("bad:cursor"), (0, "bad:cursor"))
        self.assertEqual(_build_cursor(77, "game"), "77:game")

    def test_next_page_url_resolution(self) -> None:
        current = "https://api.chess.com/pub/player/user/games/2024/07?page=1"
        data = {"page": 1, "total_pages": 3}
        next_url = _next_page_url(data, current)
        parsed = urlparse(next_url)
        query = parse_qs(parsed.query)
        self.assertEqual(query.get("page"), ["2"])

        direct = _next_page_url({"next": "https://example.com/next"}, current)
        self.assertEqual(direct, "https://example.com/next")

    def test_filter_by_cursor(self) -> None:
        rows = [
            {"game_id": "a", "last_timestamp_ms": 100},
            {"game_id": "b", "last_timestamp_ms": 100},
            {"game_id": "c", "last_timestamp_ms": 200},
        ]
        filtered = _filter_by_cursor(rows, "100:b")
        self.assertEqual([row["game_id"] for row in filtered], ["c"])

    def test_auth_headers(self) -> None:
        self.assertEqual(_auth_headers(None), {})
        self.assertEqual(_auth_headers("token"), {"Authorization": "Bearer token"})

    def test_remote_fetch_filters_by_classical_profile(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_token="token",
            chesscom_profile="classical",
            duckdb_path=self.tmp_dir / "db.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            chesscom_fixture_pgn_path=self.classical_fixture_path,
            chesscom_use_fixture_when_no_token=False,
        )
        settings.apply_source_defaults()
        settings.apply_chesscom_profile("classical")

        pgn_text = split_pgn_chunks(self.classical_fixture_path.read_text())[0]
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
                            "time_class": "rapid",
                            "pgn": pgn_text,
                            "uuid": "game-rapid",
                        },
                        {
                            "time_class": "classical",
                            "pgn": pgn_text,
                            "uuid": "game-classical",
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
        self.assertEqual(result.games[0]["game_id"], "game-classical")

    def test_remote_fetch_filters_by_correspondence_profile(self) -> None:
        settings = Settings(
            source="chesscom",
            chesscom_user="chesscom",
            chesscom_token="token",
            chesscom_profile="correspondence",
            duckdb_path=self.tmp_dir / "db.duckdb",
            chesscom_checkpoint_path=self.tmp_dir / "chesscom_since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            chesscom_fixture_pgn_path=self.correspondence_fixture_path,
            chesscom_use_fixture_when_no_token=False,
        )
        settings.apply_source_defaults()
        settings.apply_chesscom_profile("correspondence")

        pgn_text = split_pgn_chunks(self.correspondence_fixture_path.read_text())[0]
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
                            "time_class": "rapid",
                            "pgn": pgn_text,
                            "uuid": "game-rapid",
                        },
                        {
                            "time_class": "daily",
                            "pgn": pgn_text,
                            "uuid": "game-daily",
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
        self.assertEqual(result.games[0]["game_id"], "game-daily")

    def test_remote_fetch_full_history_uses_all_archives(self) -> None:
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
        archives_url = ARCHIVES_URL.format(username=settings.user)
        archive_urls = [
            f"https://api.chess.com/pub/player/{settings.user}/games/2023/{month:02d}"
            for month in range(1, 9)
        ]
        captured_urls: list[str] = []

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

        def fake_get(url, *_args, **_kwargs):
            captured_urls.append(url)
            if url == archives_url:
                return DummyResponse(200, json_data={"archives": archive_urls})
            if url in archive_urls:
                index = archive_urls.index(url)
                return DummyResponse(
                    200,
                    json_data={
                        "games": [
                            {
                                "time_class": settings.chesscom_time_class,
                                "pgn": pgn_text,
                                "uuid": f"game-{index}",
                            }
                        ]
                    },
                )
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("tactix.chesscom_client.requests.get", side_effect=fake_get):
            result = fetch_incremental_games(settings, cursor=None, full_history=True)

        self.assertEqual(len(result.games), len(archive_urls))
        self.assertIn(archive_urls[0], captured_urls)

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
