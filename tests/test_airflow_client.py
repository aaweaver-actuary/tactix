from unittest.mock import MagicMock, patch

import pytest

from tactix.fetch_dag_run__airflow_api import fetch_dag_run__airflow_api
from tactix.fetch_json__airflow_api import fetch_json__airflow_api
from tactix.gather_auth__airflow_credentials import gather_auth__airflow_credentials
from tactix.gather_url__airflow_base import gather_url__airflow_base
from tactix.orchestrate_dag_run__airflow_trigger import (
    orchestrate_dag_run__airflow_trigger,
)
from tactix.prepare_error__http_status import prepare_error__http_status
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
    assert gather_url__airflow_base(settings) == "http://localhost:8080"


def test_airflow_auth_returns_none_without_credentials() -> None:
    settings = _make_settings()
    settings.airflow_username = ""
    settings.airflow_password = ""
    assert gather_auth__airflow_credentials(settings) is None


def test_raise_for_status_raises_on_error() -> None:
    response = MagicMock()
    response.ok = False
    response.status_code = 500
    response.text = "boom"
    with pytest.raises(RuntimeError):
        prepare_error__http_status(response, "Airflow API GET /api")


def test_request_json_calls_requests() -> None:
    settings = _make_settings()
    response = MagicMock()
    response.ok = True
    response.json.return_value = {"status": "ok"}
    with patch("tactix.fetch_json__airflow_api.requests.request", return_value=response) as req:
        payload = fetch_json__airflow_api(settings, "get", "/api/v1/test")

    assert payload == {"status": "ok"}
    req.assert_called_once()


def test_trigger_and_fetch_dag_run_use_request_json() -> None:
    settings = _make_settings()
    with (
        patch(
            "tactix.orchestrate_dag_run__airflow_trigger.fetch_json__airflow_api",
            return_value={"ok": True},
        ) as trigger_request,
        patch(
            "tactix.fetch_dag_run__airflow_api.fetch_json__airflow_api",
            return_value={"ok": True},
        ) as fetch_request,
    ):
        orchestrate_dag_run__airflow_trigger(
            settings, "daily_game_sync", conf={"source": "lichess"}
        )
        fetch_dag_run__airflow_api(settings, "daily_game_sync", "run-id")

    assert trigger_request.call_count == 1
    assert fetch_request.call_count == 1
