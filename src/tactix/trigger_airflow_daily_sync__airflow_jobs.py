from __future__ import annotations

from tactix.build_airflow_conf__airflow_jobs import _airflow_conf
from tactix.get_airflow_run_id__airflow_response import _airflow_run_id
from tactix.orchestrate_dag_run__airflow_trigger import (
    orchestrate_dag_run__airflow_trigger,
)


def _trigger_airflow_daily_sync(
    settings,
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None = None,
    backfill_end_ms: int | None = None,
    triggered_at_ms: int | None = None,
) -> str:
    payload = orchestrate_dag_run__airflow_trigger(
        settings,
        "daily_game_sync",
        _airflow_conf(
            source,
            profile,
            backfill_start_ms=backfill_start_ms,
            backfill_end_ms=backfill_end_ms,
            triggered_at_ms=triggered_at_ms,
        ),
    )
    return _airflow_run_id(payload)
