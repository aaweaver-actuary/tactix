from __future__ import annotations

import os

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.utils import timezone
from dotenv import load_dotenv

from tactix.config import get_settings
from tactix.pipeline import run_daily_game_sync
from tactix.utils.logger import get_logger
from airflow.dags._dag_helpers import default_args, make_notify_dashboard_task

logger = get_logger(__name__)
load_dotenv()
CHESSCOM_USERNAME = os.getenv("CHESSCOM_USERNAME")


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

    notify_dashboard = make_notify_dashboard_task(settings, source="chesscom")
    notify_dashboard(run_pipeline())


dag = analyze_tactics_dag()
