import unittest
from datetime import date, datetime
from queue import Empty, Queue
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

import tactix.api as api
from tactix.api import _coerce_date_to_datetime, _extract_api_token, _format_sse, app
from tactix.config import Settings


def _make_request(headers: dict[str, str]) -> Request:
    header_bytes = [
        (key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()
    ]
    scope = {
        "type": "http",
        "path": "/api/dashboard",
        "method": "GET",
        "headers": header_bytes,
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "client": ("test", 1234),
    }
    return Request(scope)


class ApiHelperTests(unittest.TestCase):
    def test_extract_api_token_prefers_bearer(self) -> None:
        request = _make_request({"Authorization": "Bearer token-123"})
        self.assertEqual(_extract_api_token(request), "token-123")

    def test_extract_api_token_falls_back_to_api_key(self) -> None:
        request = _make_request({"X-API-Key": "key-456"})
        self.assertEqual(_extract_api_token(request), "key-456")

    def test_coerce_date_to_datetime_bounds(self) -> None:
        value = date(2024, 1, 2)
        start = _coerce_date_to_datetime(value)
        end = _coerce_date_to_datetime(value, end_of_day=True)

        self.assertEqual(start.date(), value)
        self.assertEqual(start.time().hour, 0)
        self.assertEqual(end.date(), value)
        self.assertEqual(end.time().hour, 23)

    def test_format_sse(self) -> None:
        payload = {"status": "ok"}
        data = _format_sse("progress", payload)

        self.assertIn(b"event: progress", data)
        self.assertIn(b'data: {"status": "ok"}', data)

    def test_airflow_conf_and_run_id_helpers(self) -> None:
        conf = api._airflow_conf(
            "chesscom",
            "blitz",
            backfill_start_ms=10,
            backfill_end_ms=None,
            triggered_at_ms=20,
        )
        self.assertEqual(conf["source"], "chesscom")
        self.assertEqual(conf["chesscom_profile"], "blitz")
        self.assertEqual(conf["backfill_start_ms"], 10)
        self.assertNotIn("backfill_end_ms", conf)
        self.assertEqual(conf["triggered_at_ms"], 20)

        lichess_conf = api._airflow_conf("lichess", "rapid")
        self.assertEqual(lichess_conf["lichess_profile"], "rapid")

        self.assertEqual(api._airflow_run_id({"dag_run_id": "abc"}), "abc")
        self.assertEqual(api._airflow_run_id({"run_id": 123}), "123")
        with self.assertRaises(ValueError):
            api._airflow_run_id({})

    def test_queue_progress_and_backfill_window(self) -> None:
        queue: Queue[object] = Queue()
        api._queue_progress(
            queue,
            "daily_game_sync",
            "start",
            message="starting",
            extra={"source": "lichess"},
        )
        event, payload = queue.get_nowait()
        self.assertEqual(event, "progress")
        self.assertEqual(payload["message"], "starting")
        self.assertEqual(payload["source"], "lichess")

        api._queue_backfill_window(queue, "daily_game_sync", None, None, 10)
        self.assertTrue(queue.empty())

        api._queue_backfill_window(queue, "daily_game_sync", 1, 2, 10)
        event, payload = queue.get_nowait()
        self.assertEqual(event, "progress")
        self.assertEqual(payload["step"], "backfill_window")

    def test_wait_for_airflow_run_success_and_timeout(self) -> None:
        settings = Settings()
        settings.airflow_poll_timeout_s = 1
        settings.airflow_poll_interval_s = 0
        queue: Queue[object] = Queue()

        with (
            patch("tactix.api._airflow_state", side_effect=["running", "success"]),
            patch("tactix.api.time_module.sleep"),
        ):
            state = api._wait_for_airflow_run(settings, queue, "job", "run-1")
        self.assertEqual(state, "success")

        with (
            patch("tactix.api._airflow_state", return_value="running"),
            patch("tactix.api.time_module.time", side_effect=[0, 0, 2]),
            patch("tactix.api.time_module.sleep"),
        ):
            with self.assertRaises(TimeoutError):
                api._wait_for_airflow_run(settings, Queue(), "job", "run-2")

    def test_cache_helpers_and_normalize_source(self) -> None:
        api._clear_dashboard_cache()
        settings = Settings()
        key = api._dashboard_cache_key(
            settings,
            "lichess",
            None,
            None,
            None,
            datetime(2024, 1, 2),
            None,
        )
        with patch("tactix.api.time_module.time", return_value=0):
            api._set_dashboard_cache(key, {"status": "ok"})
            cached = api._get_cached_dashboard_payload(key)
        self.assertEqual(cached, {"status": "ok"})

        with patch(
            "tactix.api.time_module.time",
            return_value=api._DASHBOARD_CACHE_TTL_S + 1,
        ):
            expired = api._get_cached_dashboard_payload(key)
        self.assertIsNone(expired)

        api._clear_dashboard_cache()
        with patch("tactix.api.time_module.time", return_value=0):
            for index in range(api._DASHBOARD_CACHE_MAX_ENTRIES + 1):
                api._set_dashboard_cache(("key", index), {"index": index})
        self.assertEqual(len(api._DASHBOARD_CACHE), api._DASHBOARD_CACHE_MAX_ENTRIES)
        self.assertNotIn(("key", 0), api._DASHBOARD_CACHE)

        self.assertIsNone(api._normalize_source(" ALL "))
        self.assertEqual(api._normalize_source(" ChessCom "), "chesscom")

    def test_backfill_helpers(self) -> None:
        self.assertIsNone(api._resolve_backfill_end_ms(None, None, 50))
        self.assertEqual(api._coerce_backfill_end_ms(None, 50), 50)
        self.assertEqual(api._coerce_backfill_end_ms(99, 50), 50)
        self.assertEqual(api._coerce_backfill_end_ms(30, 50), 30)
        self.assertEqual(api._resolve_backfill_end_ms(10, 99, 50), 50)

        api._validate_backfill_window(None, None)
        with self.assertRaises(HTTPException):
            api._validate_backfill_window(10, 10)

        with self.assertRaises(RuntimeError):
            api._ensure_airflow_success("failed")

    def test_trigger_airflow_daily_sync_and_state(self) -> None:
        settings = Settings()
        with patch("tactix.api.trigger_dag_run", return_value={"dag_run_id": "run-9"}) as trigger:
            run_id = api._trigger_airflow_daily_sync(settings, "lichess", "rapid")
        self.assertEqual(run_id, "run-9")
        trigger.assert_called_once()

        with patch("tactix.api.fetch_dag_run", return_value={"state": "success"}):
            state = api._airflow_state(settings, "run-9")
        self.assertEqual(state, "success")

    def test_event_stream_keep_alive(self) -> None:
        sentinel = object()

        class DummyQueue:
            def __init__(self) -> None:
                self.calls = 0

            def get(self, timeout: int = 1) -> object:
                self.calls += 1
                if self.calls == 1:
                    raise Empty
                return sentinel

        stream = api._event_stream(DummyQueue(), sentinel)
        self.assertEqual(next(stream), b"retry: 1000\n\n")
        self.assertEqual(next(stream), b": keep-alive\n\n")
        with self.assertRaises(StopIteration):
            next(stream)

    def test_run_stream_job_daily_sync_and_unsupported(self) -> None:
        settings = Settings()
        settings.airflow_enabled = False
        queue: Queue[object] = Queue()

        with patch("tactix.api.run_daily_game_sync", return_value={"status": "ok"}) as run_sync:
            result = api._run_stream_job(
                settings,
                queue,
                "daily_game_sync",
                "lichess",
                None,
                None,
                None,
                0,
                lambda _: None,
            )
        self.assertEqual(result, {"status": "ok"})
        run_sync.assert_called_once()

        with self.assertRaises(ValueError):
            api._run_stream_job(
                settings,
                queue,
                "unknown",
                None,
                None,
                None,
                None,
                0,
                lambda _: None,
            )

    def test_lifespan_primes_cache_on_startup(self) -> None:
        with patch("tactix.api._refresh_dashboard_cache_async") as refresh:
            with TestClient(app) as client:
                response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        refresh.assert_called_once_with([None, "lichess", "chesscom"])


if __name__ == "__main__":
    unittest.main()
