import unittest
from datetime import UTC, datetime

from tactix.FetchContext import FetchContext
from tactix.config import Settings
from tactix.app.use_cases.pipeline_support import _no_games_checkpoint
from tactix.utils.now import Now


class NowUtilsTests(unittest.TestCase):
    def test_now_as_datetime_is_utc(self) -> None:
        value = Now.as_datetime()
        self.assertIsInstance(value, datetime)
        self.assertEqual(value.tzinfo, UTC)

    def test_now_as_seconds_variants(self) -> None:
        self.assertIsInstance(Now.as_seconds(), float)
        self.assertIsInstance(Now.as_seconds(as_int=True), int)

    def test_now_as_milliseconds_is_int(self) -> None:
        self.assertIsInstance(Now.as_milliseconds(), int)

    def test_now_to_utc_handles_none(self) -> None:
        self.assertIsNone(Now.to_utc(None))

    def test_now_to_utc_handles_naive(self) -> None:
        value = datetime(2024, 1, 1, 12, 0, 0)
        converted = Now.to_utc(value)
        self.assertIsNotNone(converted)
        self.assertEqual(converted.tzinfo, UTC)
        self.assertEqual(converted.replace(tzinfo=None), value)

    def test_now_to_utc_handles_aware(self) -> None:
        value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        converted = Now.to_utc(value)
        self.assertEqual(converted, value)


class NoGamesCheckpointTests(unittest.TestCase):
    def test_no_games_checkpoint_uses_since_ms(self) -> None:
        settings = Settings(source="lichess")
        fetch_context = FetchContext(raw_games=[], since_ms=123)
        self.assertEqual(_no_games_checkpoint(settings, False, fetch_context), 123)

    def test_no_games_checkpoint_returns_none_for_backfill(self) -> None:
        settings = Settings(source="lichess")
        fetch_context = FetchContext(raw_games=[], since_ms=456)
        self.assertIsNone(_no_games_checkpoint(settings, True, fetch_context))

    def test_no_games_checkpoint_returns_none_for_chesscom(self) -> None:
        settings = Settings(source="chesscom")
        fetch_context = FetchContext(raw_games=[], since_ms=789)
        self.assertIsNone(_no_games_checkpoint(settings, False, fetch_context))


class StreamJobsModuleTests(unittest.TestCase):
    def test_stream_jobs_module_exports(self) -> None:
        import tactix.job_stream as stream_jobs_module

        self.assertIn("stream_jobs", stream_jobs_module.__all__)
        self.assertTrue(callable(stream_jobs_module.stream_jobs))

    def test_stream_jobs_api_exports(self) -> None:
        import tactix.job_stream as stream_jobs_api

        self.assertIn("stream_jobs", stream_jobs_api.__all__)
        self.assertIn("stream_job_by_id", stream_jobs_api.__all__)
