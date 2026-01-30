from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import task
from airflow.utils import timezone

from tactix.pipeline import get_dashboard_payload
from tactix.utils.logger import get_logger

logger = get_logger(__name__)


def default_args(*, retries: int = 2) -> dict[str, object]:
    return {
        "owner": "tactix",
        "depends_on_past": False,
        "retries": retries,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=20),
    }


def to_epoch_ms(value: datetime | None) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def resolve_profile(dag_run, source: str) -> str | None:
    if not dag_run:
        return None
    conf = getattr(dag_run, "conf", None)
    if not isinstance(conf, dict):
        return None
    if source == "chesscom":
        return conf.get("chesscom_profile") or conf.get("profile")
    return conf.get("profile") or conf.get("lichess_profile")


def resolve_backfill_window(
    dag_run,
    run_type: str,
    data_interval_start: datetime | None,
    data_interval_end: datetime | None,
) -> tuple[int | None, int | None, int | None, bool]:
    conf = getattr(dag_run, "conf", None) if dag_run else None
    conf_dict = conf if isinstance(conf, dict) else {}
    start_ms = conf_dict.get("backfill_start_ms")
    end_ms = conf_dict.get("backfill_end_ms")
    triggered_at_ms = conf_dict.get("triggered_at_ms")
    if triggered_at_ms is not None and (end_ms is None or end_ms > triggered_at_ms):
        end_ms = triggered_at_ms
    is_backfill = start_ms is not None or end_ms is not None
    if not is_backfill and run_type == "backfill":
        start_ms = to_epoch_ms(data_interval_start)
        end_ms = to_epoch_ms(data_interval_end)
        is_backfill = start_ms is not None or end_ms is not None
    return start_ms, end_ms, triggered_at_ms, is_backfill


def make_notify_dashboard_task(
    settings,
    *,
    source: str | None = None,
    task_id: str = "notify_dashboard",
):
    @task(task_id=task_id)
    def notify_dashboard(_: dict[str, object]) -> dict[str, object]:
        payload = get_dashboard_payload(settings, source=source)
        logger.info(
            "Dashboard payload refreshed; metrics_version=%s",
            payload.get("metrics_version"),
        )
        return payload

    return notify_dashboard
