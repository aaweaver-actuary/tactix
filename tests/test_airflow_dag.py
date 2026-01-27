import os
import tempfile
from pathlib import Path
import unittest

from datetime import timedelta

from airflow.models.dagbag import DagBag
from airflow.timetables.base import TimeRestriction
from airflow.utils import timezone


class AirflowDagTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_home = tempfile.mkdtemp()
        os.environ["AIRFLOW_HOME"] = self.tmp_home

    def test_daily_game_sync_dag_loads(self) -> None:
        dag_folder = Path(__file__).resolve().parents[1] / "airflow" / "dags"
        dagbag = DagBag(
            dag_folder=str(dag_folder), include_examples=False, read_dags_from_db=False
        )

        self.assertFalse(dagbag.import_errors)
        dag = dagbag.dags.get("daily_game_sync")
        self.assertIsNotNone(dag)
        self.assertEqual(dag.dag_id, "daily_game_sync")
        self.assertEqual(
            {task.task_id for task in dag.tasks},
            {
                "run_lichess_pipeline",
                "run_chesscom_pipeline",
                "log_hourly_metrics",
                "notify_dashboard",
            },
        )
        self.assertEqual(str(dag.schedule_interval), "@hourly")
        self.assertFalse(dag.catchup)
        self.assertIn("lichess", dag.tags)
        self.assertIn("chesscom", dag.tags)
        self.assertEqual(dag.default_args.get("retries"), 2)
        self.assertEqual(dag.default_args.get("retry_delay"), timedelta(minutes=5))
        self.assertTrue(dag.default_args.get("retry_exponential_backoff"))
        self.assertEqual(dag.default_args.get("max_retry_delay"), timedelta(minutes=20))
        for task_id in {
            "run_lichess_pipeline",
            "run_chesscom_pipeline",
            "notify_dashboard",
        }:
            task = dag.get_task(task_id)
            self.assertEqual(task.retries, 2)

    def test_analyze_tactics_dag_loads(self) -> None:
        dag_folder = Path(__file__).resolve().parents[1] / "airflow" / "dags"
        dagbag = DagBag(
            dag_folder=str(dag_folder), include_examples=False, read_dags_from_db=False
        )

        self.assertFalse(dagbag.import_errors)
        dag = dagbag.dags.get("analyze_tactics")
        self.assertIsNotNone(dag)
        self.assertEqual(dag.dag_id, "analyze_tactics")
        self.assertEqual(
            {task.task_id for task in dag.tasks}, {"run_pipeline", "notify_dashboard"}
        )
        self.assertEqual(str(dag.schedule_interval), "@daily")

    def test_monitor_new_positions_dag_loads(self) -> None:
        dag_folder = Path(__file__).resolve().parents[1] / "airflow" / "dags"
        dagbag = DagBag(
            dag_folder=str(dag_folder), include_examples=False, read_dags_from_db=False
        )

        self.assertFalse(dagbag.import_errors)
        dag = dagbag.dags.get("monitor_new_positions")
        self.assertIsNotNone(dag)
        self.assertEqual(dag.dag_id, "monitor_new_positions")
        self.assertEqual(
            {task.task_id for task in dag.tasks},
            {
                "monitor_lichess_positions",
                "monitor_chesscom_positions",
                "log_monitor_metrics",
                "notify_dashboard",
            },
        )
        self.assertEqual(str(dag.schedule_interval), "*/10 * * * *")
        self.assertFalse(dag.catchup)

    def test_hourly_schedule_uses_expected_execution_date(self) -> None:
        dag_folder = Path(__file__).resolve().parents[1] / "airflow" / "dags"
        dagbag = DagBag(
            dag_folder=str(dag_folder), include_examples=False, read_dags_from_db=False
        )
        dag = dagbag.dags.get("daily_game_sync")
        self.assertIsNotNone(dag)

        start = timezone.coerce_datetime(dag.start_date)
        restriction = TimeRestriction(earliest=start, latest=None, catchup=dag.catchup)
        next_info = dag.timetable.next_dagrun_info(
            last_automated_data_interval=None, restriction=restriction
        )

        self.assertIsNotNone(next_info)
        now_floor = timezone.utcnow().replace(minute=0, second=0, microsecond=0)
        self.assertGreaterEqual(next_info.logical_date, start)
        self.assertLessEqual(next_info.logical_date, now_floor)
        self.assertEqual(next_info.logical_date.minute, 0)
        self.assertEqual(next_info.logical_date.second, 0)
        self.assertEqual(
            next_info.data_interval.end - next_info.data_interval.start,
            timedelta(hours=1),
        )


if __name__ == "__main__":
    unittest.main()
