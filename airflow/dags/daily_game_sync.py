from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.utils import timezone

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
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=20),
    }


def _to_epoch_ms(value: datetime | None) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def _resolve_profile(dag_run, source: str) -> str | None:
    if not dag_run:
        return None
    conf = getattr(dag_run, "conf", None)
    if not isinstance(conf, dict):
        return None
    if source == "chesscom":
        return conf.get("chesscom_profile") or conf.get("profile")
    return conf.get("profile") or conf.get("lichess_profile")


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
    retry_args = {
        "retries": default_args()["retries"],
        "retry_delay": default_args()["retry_delay"],
        "retry_exponential_backoff": default_args()["retry_exponential_backoff"],
        "max_retry_delay": default_args()["max_retry_delay"],
    }

    @task(task_id="run_lichess_pipeline", **retry_args)
    def run_lichess_pipeline() -> dict[str, object]:
        context = get_current_context()
        logical_date = context.get("logical_date") if context else None
        dag_run = context.get("dag_run") if context else None
        run_type = str(getattr(dag_run, "run_type", "")) if dag_run else ""
        is_backfill = run_type == "backfill"
        data_interval_start = context.get("data_interval_start") if context else None
        data_interval_end = context.get("data_interval_end") if context else None
        profile = _resolve_profile(dag_run, "lichess")
        settings = get_settings(source="lichess", profile=profile)
        logger.info(
            "Starting end-to-end pipeline run for source=lichess logical_date=%s backfill=%s",
            logical_date,
            is_backfill,
        )
        result = run_daily_game_sync(
            settings,
            source="lichess",
            window_start_ms=_to_epoch_ms(data_interval_start) if is_backfill else None,
            window_end_ms=_to_epoch_ms(data_interval_end) if is_backfill else None,
            profile=profile,
        )
        result["execution_date"] = logical_date.isoformat() if logical_date else None
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
        is_backfill = run_type == "backfill"
        data_interval_start = context.get("data_interval_start") if context else None
        data_interval_end = context.get("data_interval_end") if context else None
        profile = _resolve_profile(dag_run, "chesscom")
        settings = get_settings(source="chesscom", profile=profile)
        logger.info(
            "Starting end-to-end pipeline run for source=chesscom logical_date=%s backfill=%s",
            logical_date,
            is_backfill,
        )
        result = run_daily_game_sync(
            settings,
            source="chesscom",
            window_start_ms=_to_epoch_ms(data_interval_start) if is_backfill else None,
            window_end_ms=_to_epoch_ms(data_interval_end) if is_backfill else None,
            profile=profile,
        )
        result["execution_date"] = logical_date.isoformat() if logical_date else None
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

    @task(task_id="notify_dashboard", **retry_args)
    def notify_dashboard(_: dict[str, object]) -> dict[str, object]:
        settings = get_settings()
        payload = get_dashboard_payload(settings)
        logger.info(
            "Dashboard payload refreshed; metrics_version=%s",
            payload.get("metrics_version"),
        )
        return payload

    results = [run_lichess_pipeline(), run_chesscom_pipeline()]
    notify_dashboard(log_hourly_metrics(results))


dag = daily_game_sync_dag()
