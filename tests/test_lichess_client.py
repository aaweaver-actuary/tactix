import tempfile
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import chess.pgn
import berserk

from tactix.config import Settings
from tactix.utils.logger import Logger
from tactix.infra.clients.lichess_client import (
    LichessClient,
    LichessClientContext,
    LichessFetchRequest,
    LichessTokenError,
    build_client,
    _coerce_pgn_text,
    _coerce_perf_type,
    _extract_status_code,
    _fetch_remote_games,
    _fetch_remote_games_once,
    _is_auth_error,
    _pgn_to_game_row,
    _read_cached_token,
    _refresh_lichess_token,
    _resolve_perf_value,
    _resolve_access_token,
    _write_cached_token,
    fetch_incremental_games,
    read_checkpoint,
    write_checkpoint,
)
from tactix.pgn_utils import extract_last_timestamp_ms, split_pgn_chunks
from tests.http_fakes import FakeResponse, assert_fixture_games_have_timestamps


class LichessClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_rapid_sample.pgn"
        )
        self.correspondence_fixture_path = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_correspondence_sample.pgn"
        )

    def test_checkpoint_roundtrip(self) -> None:
        ckpt_path = self.tmp_dir / "since.txt"
        self.assertIsNone(read_checkpoint(ckpt_path))
        write_checkpoint(ckpt_path, "1234:game")
        self.assertEqual(read_checkpoint(ckpt_path), "1234:game")

    def test_checkpoint_invalid_value_resets(self) -> None:
        ckpt_path = self.tmp_dir / "since_invalid.txt"
        ckpt_path.write_text("bad")
        self.assertIsNone(read_checkpoint(ckpt_path))

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
        last_ts = assert_fixture_games_have_timestamps(games, min_games=2)

        newer = fetch_incremental_games(settings, since_ms=last_ts)
        self.assertEqual(newer, [])

    def test_fixture_missing_path_returns_empty(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_missing.duckdb",
            checkpoint_path=self.tmp_dir / "since_missing.txt",
            metrics_version_file=self.tmp_dir / "metrics_missing.txt",
            fixture_pgn_path=self.tmp_dir / "missing.pgn",
            use_fixture_when_no_token=True,
        )

        games = fetch_incremental_games(settings, since_ms=0)
        self.assertEqual(games, [])

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

        filtered = fetch_incremental_games(settings, since_ms=min_ts, until_ms=max_ts + 1)

        self.assertGreater(len(filtered), 0)
        self.assertLess(len(filtered), len(games))
        self.assertTrue(all(min_ts < row["last_timestamp_ms"] < max_ts + 1 for row in filtered))

    def test_fixture_fetch_filters_blitz_window(self) -> None:
        blitz_fixture = Path(__file__).resolve().parent / "fixtures" / "lichess_blitz_sample.pgn"
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

        filtered = fetch_incremental_games(settings, since_ms=min_ts, until_ms=max_ts + 1)

        self.assertGreater(len(filtered), 0)
        self.assertLess(len(filtered), len(games))
        self.assertTrue(all(min_ts < row["last_timestamp_ms"] < max_ts + 1 for row in filtered))

    def test_fixture_fetch_filters_classical_window(self) -> None:
        classical_fixture = (
            Path(__file__).resolve().parent / "fixtures" / "lichess_classical_sample.pgn"
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

        filtered = fetch_incremental_games(settings, since_ms=min_ts, until_ms=max_ts + 1)

        self.assertGreater(len(filtered), 0)
        self.assertLess(len(filtered), len(games))
        self.assertTrue(all(min_ts < row["last_timestamp_ms"] < max_ts + 1 for row in filtered))

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

        filtered = fetch_incremental_games(settings, since_ms=min_ts, until_ms=max_ts + 1)

        self.assertGreater(len(filtered), 0)
        self.assertLess(len(filtered), len(games))
        self.assertTrue(all(min_ts < row["last_timestamp_ms"] < max_ts + 1 for row in filtered))

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

        with patch(
            "tactix.infra.clients.lichess_client.LichessClient._fetch_remote_games_once"
        ) as fetch_once:
            fetch_once.side_effect = [FakeAuthError(401), []]
            with patch(
                "tactix.infra.clients.lichess_client._refresh_lichess_token",
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

        with patch(
            "tactix.infra.clients.lichess_client.build_client",
            return_value=fake_client,
        ):
            from tactix.infra.clients import lichess_client

            result = lichess_client._fetch_remote_games_once(settings, since_ms=0)

        self.assertEqual(len(result), 1)
        games_api.export_by_player.assert_called_once()
        called_user = games_api.export_by_player.call_args[0][0]
        self.assertEqual(called_user, "envuser")

    def test_fetch_remote_games_handles_bytes_and_none(self) -> None:
        settings = Settings(
            user="envuser",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_bytes.duckdb",
            checkpoint_path=self.tmp_dir / "since_bytes.txt",
            metrics_version_file=self.tmp_dir / "metrics_bytes.txt",
            lichess_token="token",
            use_fixture_when_no_token=False,
        )
        pgn_bytes = (
            b'[Event "Fixture"]\n'
            b'[Site "https://lichess.org/abcd1234"]\n'
            b'[UTCDate "2024.06.01"]\n'
            b'[UTCTime "12:00:00"]\n'
            b'[White "envuser"]\n'
            b'[Black "opponent"]\n'
            b'[Result "1-0"]\n\n'
            b"1. e4 e5 1-0\n"
        )
        games_api = MagicMock()
        games_api.export_by_player.return_value = [None, pgn_bytes]
        fake_client = MagicMock()
        fake_client.games = games_api

        with patch(
            "tactix.infra.clients.lichess_client.build_client",
            return_value=fake_client,
        ):
            result = _fetch_remote_games_once(settings, since_ms=0)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["user"], "envuser")

    def test_fetch_remote_games_propagates_errors(self) -> None:
        settings = Settings(
            user="envuser",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_err.duckdb",
            checkpoint_path=self.tmp_dir / "since_err.txt",
            metrics_version_file=self.tmp_dir / "metrics_err.txt",
            lichess_token="token",
            use_fixture_when_no_token=False,
        )

        with patch(
            "tactix.infra.clients.lichess_client.LichessClient._fetch_remote_games_once",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                _fetch_remote_games(settings, since_ms=0)

    def test_perf_type_coercion(self) -> None:
        self.assertEqual(_coerce_perf_type("bullet"), "bullet")
        self.assertIsNone(_coerce_perf_type(None))
        self.assertIsNone(_coerce_perf_type("unknown"))

    def test_cached_token_read_write(self) -> None:
        cache_path = self.tmp_dir / "token.json"
        self.assertIsNone(_read_cached_token(cache_path))

        _write_cached_token(cache_path, "abc123")
        self.assertEqual(_read_cached_token(cache_path), "abc123")

        cache_path.write_text("raw-token")
        self.assertEqual(_read_cached_token(cache_path), "raw-token")

        cache_path.write_text("  ")
        self.assertIsNone(_read_cached_token(cache_path))

    def test_write_cached_token_handles_chmod_error(self) -> None:
        cache_path = self.tmp_dir / "token_perm.json"
        with patch(
            "tactix.infra.clients.lichess_client.os.chmod",
            side_effect=OSError("nope"),
        ):
            _write_cached_token(cache_path, "abc")
        self.assertTrue(cache_path.exists())

    def test_access_token_resolution_prefers_settings(self) -> None:
        cache_path = self.tmp_dir / "token.json"
        _write_cached_token(cache_path, "cached")
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            lichess_token_cache_path=cache_path,
            lichess_token="direct",
        )

        self.assertEqual(_resolve_access_token(settings), "direct")

        settings.lichess_token = ""
        self.assertEqual(_resolve_access_token(settings), "cached")

    def test_status_code_helpers(self) -> None:
        class DummyExc(Exception):
            def __init__(self, status_code: int) -> None:
                super().__init__("err")
                self.status_code = status_code

        exc = DummyExc(401)
        self.assertEqual(_extract_status_code(exc), 401)
        self.assertTrue(_is_auth_error(exc))

        class DummyResp:
            status_code = 403

        class DummyExcResp(Exception):
            def __init__(self) -> None:
                super().__init__("err")
                self.response = DummyResp()

        resp_exc = DummyExcResp()
        self.assertEqual(_extract_status_code(resp_exc), 403)
        self.assertTrue(_is_auth_error(resp_exc))

    def test_refresh_token_success(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_refresh.duckdb",
            checkpoint_path=self.tmp_dir / "since_refresh.txt",
            metrics_version_file=self.tmp_dir / "metrics_refresh.txt",
            lichess_oauth_refresh_token="refresh",
            lichess_oauth_client_id="client",
            lichess_oauth_client_secret="secret",
            lichess_oauth_token_url="https://lichess.org/api/token",
        )

        with patch(
            "tactix.infra.clients.lichess_client.requests.post",
            return_value=FakeResponse(json_data={"access_token": "new-token"}),
        ):
            token = _refresh_lichess_token(settings)

        self.assertEqual(token, "new-token")
        self.assertEqual(settings.lichess_token, "new-token")

    def test_refresh_token_requires_config(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_refresh2.duckdb",
            checkpoint_path=self.tmp_dir / "since_refresh2.txt",
            metrics_version_file=self.tmp_dir / "metrics_refresh2.txt",
        )

        with self.assertRaises(ValueError):
            _refresh_lichess_token(settings)

    def test_refresh_token_requires_access_token(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_refresh_missing.duckdb",
            checkpoint_path=self.tmp_dir / "since_refresh_missing.txt",
            metrics_version_file=self.tmp_dir / "metrics_refresh_missing.txt",
            lichess_oauth_refresh_token="refresh",
            lichess_oauth_client_id="client",
            lichess_oauth_client_secret="secret",
            lichess_oauth_token_url="https://lichess.org/api/token",
        )

        with patch(
            "tactix.infra.clients.lichess_client.requests.post",
            return_value=FakeResponse(json_data={}),
        ):
            with self.assertRaises(LichessTokenError):
                _refresh_lichess_token(settings)

    def test_build_client_returns_berserk_client(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_client.duckdb",
            checkpoint_path=self.tmp_dir / "since_client.txt",
            metrics_version_file=self.tmp_dir / "metrics_client.txt",
            lichess_token="token",
        )

        client = build_client(settings)
        self.assertIsInstance(client, berserk.Client)

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

        with patch(
            "tactix.infra.clients.lichess_client.build_client",
            return_value=fake_client,
        ):
            from tactix.infra.clients import lichess_client

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

        with patch(
            "tactix.infra.clients.lichess_client.build_client",
            return_value=fake_client,
        ):
            from tactix.infra.clients import lichess_client

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

        with patch(
            "tactix.infra.clients.lichess_client.build_client",
            return_value=fake_client,
        ):
            from tactix.infra.clients import lichess_client

            lichess_client._fetch_remote_games_once(settings, since_ms=0)

        _, kwargs = games_api.export_by_player.call_args
        self.assertEqual(kwargs.get("perf_type"), "correspondence")

    def test_resolve_perf_value_prefers_profile(self) -> None:
        settings = Settings(
            user="envuser",
            source="lichess",
            duckdb_path=self.tmp_dir / "db.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
            lichess_profile="blitz",
        )

        self.assertEqual(_resolve_perf_value(settings), "blitz")
        settings.lichess_profile = ""
        settings.rapid_perf = "rapid"
        self.assertEqual(_resolve_perf_value(settings), "rapid")

    def test_coerce_pgn_text_handles_bytes(self) -> None:
        self.assertEqual(_coerce_pgn_text(b"1. e4"), "1. e4")
        self.assertEqual(_coerce_pgn_text("1. d4"), "1. d4")

    def test_pgn_to_game_row_handles_none(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
        )

        self.assertIsNone(_pgn_to_game_row(None, settings))

    def test_pgn_to_game_row_builds_payload(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db.duckdb",
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
        )

        pgn_text = split_pgn_chunks(self.fixture_path.read_text())[0]
        row = _pgn_to_game_row(pgn_text, settings)
        self.assertIsNotNone(row)
        self.assertEqual(row["user"], "lichess")
        self.assertEqual(row["source"], "lichess")
        self.assertIn("pgn", row)
        self.assertIn("last_timestamp_ms", row)

    def test_lichess_client_fetch_incremental_games_fixture(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_fetch.duckdb",
            checkpoint_path=self.tmp_dir / "since_fetch.txt",
            metrics_version_file=self.tmp_dir / "metrics_fetch.txt",
            fixture_pgn_path=self.fixture_path,
            use_fixture_when_no_token=True,
        )
        client = LichessClient(LichessClientContext(settings=settings, logger=get_logger("test")))
        request = LichessFetchRequest(since_ms=0)
        result = client.fetch_incremental_games(request)

        self.assertGreaterEqual(len(result.games), 1)
        self.assertGreaterEqual(result.last_timestamp_ms, 0)

    def test_should_refresh_token_false_when_not_auth(self) -> None:
        settings = Settings(
            user="lichess",
            source="lichess",
            duckdb_path=self.tmp_dir / "db_auth.duckdb",
            checkpoint_path=self.tmp_dir / "since_auth.txt",
            metrics_version_file=self.tmp_dir / "metrics_auth.txt",
        )
        client = LichessClient(LichessClientContext(settings=settings, logger=get_logger("test")))
        self.assertFalse(client._should_refresh_token(RuntimeError("boom")))

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

        with patch(
            "tactix.infra.clients.lichess_client.build_client",
            return_value=fake_client,
        ):
            from tactix.infra.clients import lichess_client

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
