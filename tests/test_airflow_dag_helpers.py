import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from airflow.utils import timezone

from tactix.prepare_dag_helpers__airflow import (
    default_args,
    make_notify_dashboard_task,
    resolve_backfill_window,
    resolve_profile,
    to_epoch_ms,
)


class _FakeDagRun:
    def __init__(self, conf=None):
        self.conf = conf


class AirflowDagHelpersTests(unittest.TestCase):
    def test_default_args_uses_expected_values(self) -> None:
        args = default_args()
        self.assertEqual(args["owner"], "tactix")
        self.assertFalse(args["depends_on_past"])
        self.assertEqual(args["retries"], 2)
        self.assertEqual(args["retry_delay"], timedelta(minutes=5))
        self.assertTrue(args["retry_exponential_backoff"])
        self.assertEqual(args["max_retry_delay"], timedelta(minutes=20))

        custom = default_args(retries=5)
        self.assertEqual(custom["retries"], 5)

    def test_to_epoch_ms_handles_naive_and_aware(self) -> None:
        naive = datetime(2026, 1, 30, 12, 0, 0)
        expected = int(naive.replace(tzinfo=timezone.utc).timestamp() * 1000)
        self.assertEqual(to_epoch_ms(naive), expected)

        aware = timezone.datetime(2026, 1, 30, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(to_epoch_ms(aware), expected)
        self.assertIsNone(to_epoch_ms(None))

    def test_resolve_profile_reads_source_specific_conf(self) -> None:
        dag_run = _FakeDagRun({"profile": "rapid", "lichess_profile": "blitz"})
        self.assertEqual(resolve_profile(dag_run, "lichess"), "rapid")

        dag_run = _FakeDagRun({"profile": "rapid", "chesscom_profile": "bullet"})
        self.assertEqual(resolve_profile(dag_run, "chesscom"), "bullet")

        dag_run = _FakeDagRun({})
        self.assertIsNone(resolve_profile(dag_run, "lichess"))

    def test_resolve_backfill_window_prefers_conf_and_trigger(self) -> None:
        dag_run = _FakeDagRun(
            {"backfill_start_ms": 1000, "backfill_end_ms": 5000, "triggered_at_ms": 3000}
        )
        start_ms, end_ms, triggered_at_ms, is_backfill = resolve_backfill_window(
            dag_run,
            run_type="scheduled",
            data_interval_start=None,
            data_interval_end=None,
        )
        self.assertEqual(start_ms, 1000)
        self.assertEqual(end_ms, 3000)
        self.assertEqual(triggered_at_ms, 3000)
        self.assertTrue(is_backfill)

    def test_resolve_backfill_window_uses_interval_for_backfill_run(self) -> None:
        start = timezone.datetime(2026, 1, 30, 9, 0, 0, tzinfo=timezone.utc)
        end = timezone.datetime(2026, 1, 30, 10, 0, 0, tzinfo=timezone.utc)
        start_ms, end_ms, triggered_at_ms, is_backfill = resolve_backfill_window(
            _FakeDagRun(None),
            run_type="backfill",
            data_interval_start=start,
            data_interval_end=end,
        )
        self.assertEqual(start_ms, int(start.timestamp() * 1000))
        self.assertEqual(end_ms, int(end.timestamp() * 1000))
        self.assertIsNone(triggered_at_ms)
        self.assertTrue(is_backfill)

    def test_make_notify_dashboard_task_uses_payload(self) -> None:
        with patch(
            "tactix.prepare_dag_helpers__airflow.get_dashboard_payload"
        ) as get_payload:
            get_payload.return_value = {"metrics_version": 42}
            notify = make_notify_dashboard_task(settings=object(), source="lichess")
            callable_fn = (
                getattr(notify, "function", None)
                or getattr(notify, "python_callable", None)
                or getattr(notify, "__wrapped__", None)
            )
            self.assertIsNotNone(callable_fn)
            payload = callable_fn({})
        self.assertEqual(payload["metrics_version"], 42)


if __name__ == "__main__":
    unittest.main()
