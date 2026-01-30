from __future__ import annotations

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.utils import timezone

from tactix.config import get_settings
from tactix.pipeline import run_daily_game_sync
from tactix.utils.logger import get_logger
from airflow.dags._dag_helpers import (
    default_args,
    make_notify_dashboard_task,
    resolve_backfill_window,
    resolve_profile,
)

logger = get_logger(__name__)


@dag(
    dag_id="daily_game_sync",
    schedule="@hourly",
    start_date=timezone.datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args(),
    tags=["lichess", "chesscom", "tactix"],
    description="Fetch chess games (Lichess or Chess.com), extract positions, run tactics, refresh metrics",
)
def daily_game_sync_dag():
    dag_defaults = default_args()
    retry_args = {
        "retries": dag_defaults["retries"],
        "retry_delay": dag_defaults["retry_delay"],
        "retry_exponential_backoff": dag_defaults["retry_exponential_backoff"],
        "max_retry_delay": dag_defaults["max_retry_delay"],
    }

    @task(task_id="run_lichess_pipeline", **retry_args)
    def run_lichess_pipeline() -> dict[str, object]:
        context = get_current_context()
        logical_date = context.get("logical_date") if context else None
        dag_run = context.get("dag_run") if context else None
        run_type = str(getattr(dag_run, "run_type", "")) if dag_run else ""
        data_interval_start = context.get("data_interval_start") if context else None
        data_interval_end = context.get("data_interval_end") if context else None
        (
            backfill_start_ms,
            backfill_end_ms,
            triggered_at_ms,
            is_backfill,
        ) = resolve_backfill_window(dag_run, run_type, data_interval_start, data_interval_end)
        profile = resolve_profile(dag_run, "lichess")
        settings = get_settings(source="lichess", profile=profile)
        logger.info(
            "Starting end-to-end pipeline run for source=lichess logical_date=%s backfill=%s backfill_start_ms=%s backfill_end_ms=%s triggered_at_ms=%s",
            logical_date,
            is_backfill,
            backfill_start_ms,
            backfill_end_ms,
            triggered_at_ms,
        )
        result = run_daily_game_sync(
            settings,
            source="lichess",
            window_start_ms=backfill_start_ms if is_backfill else None,
            window_end_ms=backfill_end_ms if is_backfill else None,
            profile=profile,
        )
        result["execution_date"] = logical_date.isoformat() if logical_date else None
        result["backfill_start_ms"] = backfill_start_ms if is_backfill else None
        result["backfill_end_ms"] = backfill_end_ms if is_backfill else None
        result["triggered_at_ms"] = triggered_at_ms if is_backfill else None
        logger.info(
            "Pipeline run succeeded: source=%s fetched_games=%s raw_pgns_inserted=%s raw_pgns_hashed=%s raw_pgns_matched=%s positions=%s tactics=%s metrics_version=%s",
            result.get("source"),
            result.get("fetched_games"),
            result.get("raw_pgns_inserted"),
            result.get("raw_pgns_hashed"),
            result.get("raw_pgns_matched"),
            result.get("positions"),
            result.get("tactics"),
            result.get("metrics_version"),
        )
        return result

    @task(task_id="run_chesscom_pipeline", **retry_args)
    def run_chesscom_pipeline() -> dict[str, object]:
        context = get_current_context()
        logical_date = context.get("logical_date") if context else None
        dag_run = context.get("dag_run") if context else None
        run_type = str(getattr(dag_run, "run_type", "")) if dag_run else ""
        data_interval_start = context.get("data_interval_start") if context else None
        data_interval_end = context.get("data_interval_end") if context else None
        (
            backfill_start_ms,
            backfill_end_ms,
            triggered_at_ms,
            is_backfill,
        ) = resolve_backfill_window(dag_run, run_type, data_interval_start, data_interval_end)
        profile = resolve_profile(dag_run, "chesscom")
        settings = get_settings(source="chesscom", profile=profile)
        logger.info(
            "Starting end-to-end pipeline run for source=chesscom logical_date=%s backfill=%s backfill_start_ms=%s backfill_end_ms=%s triggered_at_ms=%s",
            logical_date,
            is_backfill,
            backfill_start_ms,
            backfill_end_ms,
            triggered_at_ms,
        )
        result = run_daily_game_sync(
            settings,
            source="chesscom",
            window_start_ms=backfill_start_ms if is_backfill else None,
            window_end_ms=backfill_end_ms if is_backfill else None,
            profile=profile,
        )
        result["execution_date"] = logical_date.isoformat() if logical_date else None
        result["backfill_start_ms"] = backfill_start_ms if is_backfill else None
        result["backfill_end_ms"] = backfill_end_ms if is_backfill else None
        result["triggered_at_ms"] = triggered_at_ms if is_backfill else None
        logger.info(
            "Pipeline run succeeded: source=%s fetched_games=%s raw_pgns_inserted=%s raw_pgns_hashed=%s raw_pgns_matched=%s positions=%s tactics=%s metrics_version=%s",
            result.get("source"),
            result.get("fetched_games"),
            result.get("raw_pgns_inserted"),
            result.get("raw_pgns_hashed"),
            result.get("raw_pgns_matched"),
            result.get("positions"),
            result.get("tactics"),
            result.get("metrics_version"),
        )
        return result

    @task(task_id="log_hourly_metrics")
    def log_hourly_metrics(results: list[dict[str, object]]) -> dict[str, object]:
        for result in results:
            logger.info(
                "Hourly metrics summary: source=%s fetched_games=%s raw_pgns_inserted=%s raw_pgns_hashed=%s raw_pgns_matched=%s positions=%s tactics=%s metrics_version=%s",
                result.get("source"),
                result.get("fetched_games"),
                result.get("raw_pgns_inserted"),
                result.get("raw_pgns_hashed"),
                result.get("raw_pgns_matched"),
                result.get("positions"),
                result.get("tactics"),
                result.get("metrics_version"),
            )
        return {"run_count": len(results)}

    results = [run_lichess_pipeline(), run_chesscom_pipeline()]
    settings = get_settings()
    notify_dashboard = make_notify_dashboard_task(settings)
    notify_dashboard(log_hourly_metrics(results))


dag = daily_game_sync_dag()
