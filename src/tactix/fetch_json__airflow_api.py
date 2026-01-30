from __future__ import annotations

from typing import Any

import requests

from tactix.config import Settings
from tactix.gather_auth__airflow_credentials import gather_auth__airflow_credentials
from tactix.gather_url__airflow_base import gather_url__airflow_base
from tactix.prepare_error__http_status import prepare_error__http_status


def fetch_json__airflow_api(
    settings: Settings, method: str, path: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Perform an Airflow API request and return JSON.

    Args:
        settings: Application settings containing Airflow configuration.
        method: HTTP method to use.
        path: API path to request.
        payload: Optional JSON payload.

    Returns:
        Parsed JSON response.
    """
    url = f"{gather_url__airflow_base(settings)}{path}"
    response = requests.request(
        method,
        url,
        json=payload,
        auth=gather_auth__airflow_credentials(settings),
        headers={"Accept": "application/json"},
        timeout=settings.airflow_api_timeout_s,
    )
    prepare_error__http_status(response, f"Airflow API {method.upper()} {path}")
    return response.json()
