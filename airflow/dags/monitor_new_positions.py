from __future__ import annotations

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.utils import timezone

from tactix.config import get_settings
from tactix.pipeline import run_monitor_new_positions
from tactix.utils.logger import Logger
from tactix.prepare_dag_helpers__airflow import (
    default_args,
    make_notify_dashboard_task,
    resolve_profile,
)

logger = Logger(__name__)


@dag(
    dag_id="monitor_new_positions",
    schedule="*/10 * * * *",
    start_date=timezone.datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args(),
    tags=["lichess", "chesscom", "tactix", "monitor"],
    description="Monitor new raw PGNs and run tactics analysis for newly extracted positions",
)
def monitor_new_positions_dag():
    dag_defaults = default_args()
    retry_args = {
        "retries": dag_defaults["retries"],
        "retry_delay": dag_defaults["retry_delay"],
        "retry_exponential_backoff": dag_defaults["retry_exponential_backoff"],
        "max_retry_delay": dag_defaults["max_retry_delay"],
    }

    @task(task_id="monitor_lichess_positions", **retry_args)
    def monitor_lichess_positions() -> dict[str, object]:
        context = get_current_context()
        logical_date = context.get("logical_date") if context else None
        dag_run = context.get("dag_run") if context else None
        profile = resolve_profile(dag_run, "lichess")
        settings = get_settings(source="lichess", profile=profile)
        logger.info(
            "Monitoring new positions: source=lichess logical_date=%s profile=%s",
            logical_date,
            profile,
        )
        result = run_monitor_new_positions(settings, source="lichess", profile=profile)
        result["execution_date"] = logical_date.isoformat() if logical_date else None
        logger.info(
            "Monitor results: source=%s raw_pgns_checked=%s new_games=%s positions_extracted=%s positions_analyzed=%s tactics_detected=%s metrics_version=%s",
            result.get("source"),
            result.get("raw_pgns_checked"),
            result.get("new_games"),
            result.get("positions_extracted"),
            result.get("positions_analyzed"),
            result.get("tactics_detected"),
            result.get("metrics_version"),
        )
        return result

    @task(task_id="monitor_chesscom_positions", **retry_args)
    def monitor_chesscom_positions() -> dict[str, object]:
        context = get_current_context()
        logical_date = context.get("logical_date") if context else None
        dag_run = context.get("dag_run") if context else None
        profile = resolve_profile(dag_run, "chesscom")
        settings = get_settings(source="chesscom", profile=profile)
        logger.info(
            "Monitoring new positions: source=chesscom logical_date=%s profile=%s",
            logical_date,
            profile,
        )
        result = run_monitor_new_positions(settings, source="chesscom", profile=profile)
        result["execution_date"] = logical_date.isoformat() if logical_date else None
        logger.info(
            "Monitor results: source=%s raw_pgns_checked=%s new_games=%s positions_extracted=%s positions_analyzed=%s tactics_detected=%s metrics_version=%s",
            result.get("source"),
            result.get("raw_pgns_checked"),
            result.get("new_games"),
            result.get("positions_extracted"),
            result.get("positions_analyzed"),
            result.get("tactics_detected"),
            result.get("metrics_version"),
        )
        return result

    @task(task_id="log_monitor_metrics")
    def log_monitor_metrics(results: list[dict[str, object]]) -> dict[str, object]:
        for result in results:
            logger.info(
                "Monitor metrics summary: source=%s positions_analyzed=%s tactics_detected=%s",
                result.get("source"),
                result.get("positions_analyzed"),
                result.get("tactics_detected"),
            )
        return {"run_count": len(results)}

    results = [monitor_lichess_positions(), monitor_chesscom_positions()]
    settings = get_settings()
    notify_dashboard = make_notify_dashboard_task(settings)
    notify_dashboard(log_monitor_metrics(results))


dag = monitor_new_positions_dag()
