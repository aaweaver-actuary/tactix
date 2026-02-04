"""Fetch Airflow DAG run payloads."""

from __future__ import annotations

from typing import Any

from tactix.config import Settings
from tactix.fetch_json__airflow_api import fetch_json__airflow_api


def fetch_dag_run__airflow_api(settings: Settings, dag_id: str, run_id: str) -> dict[str, Any]:
    """Fetch a specific Airflow DAG run via the API.

    Args:
        settings: Application settings.
        dag_id: Airflow DAG identifier.
        run_id: DAG run identifier.

    Returns:
        Airflow DAG run payload.
    """
    return fetch_json__airflow_api(settings, "get", f"/api/v1/dags/{dag_id}/dagRuns/{run_id}")
