from __future__ import annotations

from datetime import datetime, timedelta
from typing import SupportsInt, cast

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


def _dag_run_conf(dag_run) -> dict[str, object] | None:
    if not dag_run:
        return None
    conf = getattr(dag_run, "conf", None)
    if isinstance(conf, dict):
        return conf
    return None


def _first_conf_value(conf: dict[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = conf.get(key)
        if value:
            return str(value)
    return None


def _coerce_optional_int(value: object | None) -> int | None:
    if value is None:
        return None
    try:
        return int(cast(SupportsInt | str | bytes | bytearray, value))
    except (TypeError, ValueError):
        return None


def resolve_profile(dag_run, source: str) -> str | None:
    conf = _dag_run_conf(dag_run)
    if not conf:
        return None
    if source == "chesscom":
        return _first_conf_value(conf, ("chesscom_profile", "profile"))
    return _first_conf_value(conf, ("profile", "lichess_profile"))


def _read_backfill_conf(conf: dict[str, object]) -> tuple[int | None, int | None, int | None]:
    start_ms = _coerce_optional_int(conf.get("backfill_start_ms"))
    end_ms = _coerce_optional_int(conf.get("backfill_end_ms"))
    triggered_at_ms = _coerce_optional_int(conf.get("triggered_at_ms"))
    return start_ms, end_ms, triggered_at_ms


def _apply_triggered_end(end_ms: int | None, triggered_at_ms: int | None) -> int | None:
    if triggered_at_ms is None:
        return end_ms
    if end_ms is None or end_ms > triggered_at_ms:
        return triggered_at_ms
    return end_ms


def _backfill_from_interval(
    run_type: str,
    data_interval_start: datetime | None,
    data_interval_end: datetime | None,
) -> tuple[int | None, int | None]:
    if run_type != "backfill":
        return None, None
    return to_epoch_ms(data_interval_start), to_epoch_ms(data_interval_end)


def resolve_backfill_window(
    dag_run,
    run_type: str,
    data_interval_start: datetime | None,
    data_interval_end: datetime | None,
) -> tuple[int | None, int | None, int | None, bool]:
    conf = _dag_run_conf(dag_run) or {}
    start_ms, end_ms, triggered_at_ms = _read_backfill_conf(conf)
    end_ms = _apply_triggered_end(end_ms, triggered_at_ms)
    is_backfill = start_ms is not None or end_ms is not None
    if not is_backfill:
        interval_start, interval_end = _backfill_from_interval(
            run_type,
            data_interval_start,
            data_interval_end,
        )
        start_ms = interval_start
        end_ms = interval_end
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


__all__ = [
    "default_args",
    "make_notify_dashboard_task",
    "resolve_backfill_window",
    "resolve_profile",
    "to_epoch_ms",
]

# References to avoid vulture reporting these helpers as unused when only
# Airflow DAG modules import them.
_USED_BY_AIRFLOW = (
    default_args,
    make_notify_dashboard_task,
    resolve_backfill_window,
    resolve_profile,
    to_epoch_ms,
)
