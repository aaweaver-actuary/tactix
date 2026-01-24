import os
import tempfile
from pathlib import Path
import unittest

from airflow.models.dagbag import DagBag


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


if __name__ == "__main__":
    unittest.main()
