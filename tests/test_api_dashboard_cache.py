import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from tactix.api import (
    _DASHBOARD_CACHE_TTL_S,
    _clear_dashboard_cache,
    _dashboard_cache_key,
    _get_cached_dashboard_payload,
    _set_dashboard_cache,
    app,
)
from tactix.config import get_settings


class ApiDashboardCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_dashboard_cache()

    def tearDown(self) -> None:
        _clear_dashboard_cache()

    def test_dashboard_cache_round_trip(self) -> None:
        settings = get_settings()
        key = _dashboard_cache_key(
            settings,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        payload = {"source": "all", "metrics_version": 5}

        with patch("tactix.api.time_module.time", return_value=1000.0):
            _set_dashboard_cache(key, payload)
            cached = _get_cached_dashboard_payload(key)

        self.assertEqual(cached, payload)

    def test_dashboard_cache_expires(self) -> None:
        settings = get_settings()
        key = _dashboard_cache_key(
            settings,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        payload = {"source": "all", "metrics_version": 7}

        with patch("tactix.api.time_module.time", return_value=0.0):
            _set_dashboard_cache(key, payload)

        with patch("tactix.api.time_module.time", return_value=float(_DASHBOARD_CACHE_TTL_S + 1)):
            cached = _get_cached_dashboard_payload(key)

        self.assertIsNone(cached)

    def test_dashboard_endpoint_uses_cached_payload(self) -> None:
        payload = {"status": "ok", "metrics_version": 11}

        client = TestClient(app)
        token = get_settings().api_token
        with (
            patch("tactix.api._get_cached_dashboard_payload", return_value=payload),
            patch("tactix.api.get_dashboard_payload") as get_payload,
        ):
            response = client.get(
                "/api/dashboard",
                headers={"Authorization": f"Bearer {token}"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        get_payload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
