from __future__ import annotations

from typing import Any

import requests

from tactix.config import Settings


def _airflow_base_url(settings: Settings) -> str:
    return settings.airflow_base_url.rstrip("/")


def _airflow_auth(settings: Settings) -> tuple[str, str] | None:
    if not settings.airflow_username or not settings.airflow_password:
        return None
    return (settings.airflow_username, settings.airflow_password)


def _raise_for_status(response: requests.Response, context: str) -> None:
    if response.ok:
        return
    raise RuntimeError(
        f"{context}: {response.status_code} {response.text.strip()}".strip()
    )


def _request_json(
    settings: Settings, method: str, path: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    url = f"{_airflow_base_url(settings)}{path}"
    response = requests.request(
        method,
        url,
        json=payload,
        auth=_airflow_auth(settings),
        headers={"Accept": "application/json"},
        timeout=settings.airflow_api_timeout_s,
    )
    _raise_for_status(response, f"Airflow API {method.upper()} {path}")
    return response.json()


def trigger_dag_run(
    settings: Settings, dag_id: str, conf: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload = {"conf": conf or {}}
    return _request_json(settings, "post", f"/api/v1/dags/{dag_id}/dagRuns", payload)


def fetch_dag_run(settings: Settings, dag_id: str, run_id: str) -> dict[str, Any]:
    return _request_json(settings, "get", f"/api/v1/dags/{dag_id}/dagRuns/{run_id}")
