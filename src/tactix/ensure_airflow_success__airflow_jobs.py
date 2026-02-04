"""Validate Airflow job run states."""

from __future__ import annotations


def _ensure_airflow_success(state: str) -> None:
    """Raise when the airflow state indicates failure."""
    if state != "success":
        raise RuntimeError(f"Airflow run failed with state={state}")
