from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task

from tactix.config import get_settings
from tactix.logging_utils import get_logger
from tactix.pipeline import get_dashboard_payload, run_daily_game_sync

logger = get_logger(__name__)


def default_args():
    return {
        "owner": "tactix",
        "depends_on_past": False,
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    }


@dag(
    dag_id="daily_game_sync",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args(),
    tags=["lichess", "tactix"],
    description="Fetch Lichess rapid games, extract positions, run tactics, refresh metrics",
)
def daily_game_sync_dag():
    settings = get_settings()

    @task(task_id="run_pipeline")
    def run_pipeline() -> dict[str, object]:
        logger.info("Starting end-to-end pipeline run")
        return run_daily_game_sync(settings)

    @task(task_id="notify_dashboard")
    def notify_dashboard(_: dict[str, object]) -> dict[str, object]:
        payload = get_dashboard_payload(settings)
        logger.info(
            "Dashboard payload refreshed; metrics_version=%s",
            payload.get("metrics_version"),
        )
        return payload

    notify_dashboard(run_pipeline())


dag = daily_game_sync_dag()
