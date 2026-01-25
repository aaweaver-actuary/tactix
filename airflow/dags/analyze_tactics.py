from __future__ import annotations

from datetime import timedelta
import os

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.utils import timezone
from dotenv import load_dotenv

from tactix.config import get_settings
from tactix.logging_utils import get_logger
from tactix.pipeline import get_dashboard_payload, run_daily_game_sync

logger = get_logger(__name__)
load_dotenv()
CHESSCOM_USERNAME = os.getenv("CHESSCOM_USERNAME")


def default_args():
    return {
        "owner": "tactix",
        "depends_on_past": False,
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=20),
    }


@dag(
    dag_id="analyze_tactics",
    schedule="@daily",
    start_date=timezone.datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args(),
    tags=["chesscom", "tactix", "analysis"],
    description="Analyze Chess.com tactics with Stockfish and refresh metrics",
)
def analyze_tactics_dag():
    settings = get_settings(source="chesscom")
    if CHESSCOM_USERNAME:
        settings.chesscom_user = CHESSCOM_USERNAME
        settings.user = CHESSCOM_USERNAME

    @task(task_id="run_pipeline")
    def run_pipeline() -> dict[str, object]:
        context = get_current_context()
        logical_date = context.get("logical_date") if context else None
        logger.info(
            "Starting tactics analysis for source=%s logical_date=%s",
            settings.source,
            logical_date,
        )
        result = run_daily_game_sync(settings, source="chesscom")
        result["execution_date"] = logical_date.isoformat() if logical_date else None
        return result

    @task(task_id="notify_dashboard")
    def notify_dashboard(_: dict[str, object]) -> dict[str, object]:
        payload = get_dashboard_payload(settings, source="chesscom")
        logger.info(
            "Dashboard payload refreshed; metrics_version=%s",
            payload.get("metrics_version"),
        )
        return payload

    notify_dashboard(run_pipeline())


dag = analyze_tactics_dag()
