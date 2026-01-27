from unittest.mock import MagicMock, patch

import pytest

from tactix.airflow_client import (
    _airflow_auth,
    _airflow_base_url,
    _raise_for_status,
    _request_json,
    fetch_dag_run,
    trigger_dag_run,
)
from tactix.config import Settings


def _make_settings() -> Settings:
    settings = Settings()
    settings.airflow_base_url = "http://localhost:8080/"
    settings.airflow_username = "admin"
    settings.airflow_password = "admin"
    settings.airflow_api_timeout_s = 5
    return settings


def test_airflow_base_url_strips_trailing_slash() -> None:
    settings = _make_settings()
    assert _airflow_base_url(settings) == "http://localhost:8080"


def test_airflow_auth_returns_none_without_credentials() -> None:
    settings = _make_settings()
    settings.airflow_username = ""
    settings.airflow_password = ""
    assert _airflow_auth(settings) is None


def test_raise_for_status_raises_on_error() -> None:
    response = MagicMock()
    response.ok = False
    response.status_code = 500
    response.text = "boom"
    with pytest.raises(RuntimeError):
        _raise_for_status(response, "Airflow API GET /api")


def test_request_json_calls_requests() -> None:
    settings = _make_settings()
    response = MagicMock()
    response.ok = True
    response.json.return_value = {"status": "ok"}
    with patch("tactix.airflow_client.requests.request", return_value=response) as req:
        payload = _request_json(settings, "get", "/api/v1/test")

    assert payload == {"status": "ok"}
    req.assert_called_once()


def test_trigger_and_fetch_dag_run_use_request_json() -> None:
    settings = _make_settings()
    with patch(
        "tactix.airflow_client._request_json", return_value={"ok": True}
    ) as request_json:
        trigger_dag_run(settings, "daily_game_sync", conf={"source": "lichess"})
        fetch_dag_run(settings, "daily_game_sync", "run-id")

    assert request_json.call_count == 2
