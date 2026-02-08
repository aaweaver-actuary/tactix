"""Fetch the current Airflow DAG run state."""

from __future__ import annotations

from tactix.fetch_dag_run__airflow_api import fetch_dag_run__airflow_api


def _airflow_state(settings, run_id: str) -> str:
    payload = fetch_dag_run__airflow_api(settings, "daily_game_sync", run_id)
    return str(payload.get("state") or "unknown")
