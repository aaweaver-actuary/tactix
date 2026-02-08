"""Check whether Airflow is enabled."""

from __future__ import annotations


def _airflow_enabled(settings) -> bool:
    return settings.airflow_enabled and bool(settings.airflow_base_url)
