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


def _resolve_profile(dag_run) -> str | None:
    if not dag_run:
        return None
    conf = getattr(dag_run, "conf", None)
    if isinstance(conf, dict):
        return conf.get("profile") or conf.get("lichess_profile")
    return None


@dag(
    dag_id="daily_game_sync",
    schedule="@daily",
    start_date=timezone.datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args(),
    tags=["lichess", "chesscom", "tactix"],
    description="Fetch chess games (Lichess or Chess.com), extract positions, run tactics, refresh metrics",
)
def daily_game_sync_dag():
    @task(task_id="run_pipeline")
    def run_pipeline() -> dict[str, object]:
        context = get_current_context()
        logical_date = context.get("logical_date") if context else None
        dag_run = context.get("dag_run") if context else None
        run_type = str(getattr(dag_run, "run_type", "")) if dag_run else ""
        is_backfill = run_type == "backfill"
        data_interval_start = context.get("data_interval_start") if context else None
        data_interval_end = context.get("data_interval_end") if context else None
        settings = get_settings()
        profile = _resolve_profile(dag_run) or settings.lichess_profile or None
        logger.info(
            "Starting end-to-end pipeline run for source=%s logical_date=%s backfill=%s",
            settings.source,
            logical_date,
            is_backfill,
        )
        result = run_daily_game_sync(
            settings,
            window_start_ms=_to_epoch_ms(data_interval_start) if is_backfill else None,
            window_end_ms=_to_epoch_ms(data_interval_end) if is_backfill else None,
            profile=profile,
        )
        result["execution_date"] = logical_date.isoformat() if logical_date else None
        logger.info(
            "Pipeline run succeeded: source=%s fetched_games=%s raw_pgns_inserted=%s positions=%s tactics=%s metrics_version=%s",
            result.get("source"),
            result.get("fetched_games"),
            result.get("raw_pgns_inserted"),
            result.get("positions"),
            result.get("tactics"),
            result.get("metrics_version"),
        )
        return result

    @task(task_id="notify_dashboard")
    def notify_dashboard(_: dict[str, object]) -> dict[str, object]:
        settings = get_settings()
        payload = get_dashboard_payload(settings)
        logger.info(
            "Dashboard payload refreshed; metrics_version=%s",
            payload.get("metrics_version"),
        )
        return payload

    notify_dashboard(run_pipeline())


dag = daily_game_sync_dag()
