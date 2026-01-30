from __future__ import annotations

from typing import Any

from tactix.config import Settings
from tactix.fetch_json__airflow_api import fetch_json__airflow_api


def orchestrate_dag_run__airflow_trigger(
    settings: Settings, dag_id: str, conf: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Trigger an Airflow DAG run via the API.

    Args:
        settings: Application settings.
        dag_id: Airflow DAG identifier.
        conf: Optional DAG run configuration.

    Returns:
        Airflow DAG run payload.
    """
    payload = {"conf": conf or {}}
    return fetch_json__airflow_api(settings, "post", f"/api/v1/dags/{dag_id}/dagRuns", payload)
