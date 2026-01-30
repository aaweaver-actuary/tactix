from __future__ import annotations


def _ensure_airflow_success(state: str) -> None:
    if state != "success":
        raise RuntimeError(f"Airflow run failed with state={state}")
