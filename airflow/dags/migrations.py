from __future__ import annotations

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.utils import timezone

from tactix.config import get_settings
from tactix.pipeline import run_migrations
from tactix.utils.logger import get_logger
from tactix.airflow_dag_helpers import default_args

logger = get_logger(__name__)


@dag(
    dag_id="migrations",
    schedule=None,
    start_date=timezone.datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args(retries=1),
    tags=["migrations", "duckdb", "lichess", "chesscom", "tactix"],
    description="Run DuckDB schema migrations safely across versions",
)
def migrations_dag():
    settings = get_settings()

    @task(task_id="run_migrations")
    def run_migrations_task() -> dict[str, object]:
        context = get_current_context()
        logical_date = context.get("logical_date") if context else None
        logger.info(
            "Running DuckDB migrations for source=%s logical_date=%s",
            settings.source,
            logical_date,
        )
        result = run_migrations(settings)
        result["execution_date"] = logical_date.isoformat() if logical_date else None
        return result

    run_migrations_task()


dag = migrations_dag()
