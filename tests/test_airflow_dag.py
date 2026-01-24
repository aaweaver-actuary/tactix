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
            {task.task_id for task in dag.tasks}, {"run_pipeline", "notify_dashboard"}
        )
        self.assertEqual(str(dag.schedule_interval), "@daily")

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

    def test_daily_schedule_uses_expected_execution_date(self) -> None:
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
        today = timezone.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        self.assertGreaterEqual(next_info.logical_date, start)
        self.assertEqual(next_info.logical_date, today - timedelta(days=1))
        self.assertEqual(
            next_info.data_interval.end - next_info.data_interval.start,
            timedelta(days=1),
        )


if __name__ == "__main__":
    unittest.main()
