from __future__ import annotations

from typing import cast

from tactix.airflow_daily_sync_context import AirflowDailySyncTriggerContext
from tactix.build_airflow_conf__airflow_jobs import _airflow_conf
from tactix.config import Settings
from tactix.get_airflow_run_id__airflow_response import _airflow_run_id
from tactix.legacy_args import apply_legacy_args, apply_legacy_kwargs, init_legacy_values
from tactix.orchestrate_dag_run__airflow_trigger import (
    orchestrate_dag_run__airflow_trigger,
)


def _trigger_airflow_daily_sync(
    context: AirflowDailySyncTriggerContext | Settings,
    *args: object,
    **legacy: object,
) -> str:
    if isinstance(context, AirflowDailySyncTriggerContext):
        resolved = context
    else:
        ordered_keys = (
            "source",
            "profile",
            "backfill_start_ms",
            "backfill_end_ms",
            "triggered_at_ms",
        )
        values = init_legacy_values(ordered_keys)
        apply_legacy_kwargs(values, ordered_keys, legacy)
        apply_legacy_args(values, ordered_keys, args)
        resolved = AirflowDailySyncTriggerContext(
            settings=context,
            source=cast(str | None, values["source"]),
            profile=cast(str | None, values["profile"]),
            backfill_start_ms=cast(int | None, values["backfill_start_ms"]),
            backfill_end_ms=cast(int | None, values["backfill_end_ms"]),
            triggered_at_ms=cast(int | None, values["triggered_at_ms"]),
        )
    payload = orchestrate_dag_run__airflow_trigger(
        resolved.settings,
        "daily_game_sync",
        _airflow_conf(
            resolved.source,
            resolved.profile,
            backfill_start_ms=resolved.backfill_start_ms,
            backfill_end_ms=resolved.backfill_end_ms,
            triggered_at_ms=resolved.triggered_at_ms,
        ),
    )
    return _airflow_run_id(payload)
