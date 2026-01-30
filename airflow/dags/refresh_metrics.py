from __future__ import annotations

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.utils import timezone

from tactix.config import get_settings
from tactix.pipeline import run_refresh_metrics
from tactix.utils.logger import get_logger
from airflow.dags._dag_helpers import default_args, make_notify_dashboard_task

logger = get_logger(__name__)
@dag(
    dag_id="refresh_metrics",
    schedule="@daily",
    start_date=timezone.datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args(),
    tags=["metrics", "lichess", "chesscom", "tactix"],
    description="Refresh metrics summaries and update dashboard payloads",
)
def refresh_metrics_dag():
    settings = get_settings()

    @task(task_id="refresh_metrics")
    def refresh_metrics() -> dict[str, object]:
        context = get_current_context()
        logical_date = context.get("logical_date") if context else None
        logger.info(
            "Refreshing metrics for source=%s logical_date=%s",
            settings.source,
            logical_date,
        )
        result = run_refresh_metrics(settings)
        result["execution_date"] = logical_date.isoformat() if logical_date else None
        return result

    notify_dashboard = make_notify_dashboard_task(settings)
    notify_dashboard(refresh_metrics())


dag = refresh_metrics_dag()
