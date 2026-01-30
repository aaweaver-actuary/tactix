from __future__ import annotations


def _airflow_run_id(payload: dict[str, object]) -> str:
    run_id = payload.get("dag_run_id") or payload.get("run_id")
    if not run_id:
        raise ValueError("Airflow response missing dag_run_id")
    return str(run_id)
