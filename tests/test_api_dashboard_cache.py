import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from tactix.api import app
from tactix.build_dashboard_cache_key__api_cache import _dashboard_cache_key
from tactix.clear_dashboard_cache__api_cache import _clear_dashboard_cache
from tactix.dashboard_cache_state__api_cache import _DASHBOARD_CACHE_TTL_S
from tactix.get_cached_dashboard_payload__api_cache import _get_cached_dashboard_payload
from tactix.set_dashboard_cache__api_cache import _set_dashboard_cache
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

        with (
            patch("tactix.set_dashboard_cache__api_cache.time_module.time", return_value=1000.0),
            patch(
                "tactix.get_cached_dashboard_payload__api_cache.time_module.time",
                return_value=1000.0,
            ),
        ):
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

        with patch("tactix.set_dashboard_cache__api_cache.time_module.time", return_value=0.0):
            _set_dashboard_cache(key, payload)

        with patch(
            "tactix.get_cached_dashboard_payload__api_cache.time_module.time",
            return_value=float(_DASHBOARD_CACHE_TTL_S + 1),
        ):
            cached = _get_cached_dashboard_payload(key)

        self.assertIsNone(cached)

    def test_dashboard_endpoint_uses_cached_payload(self) -> None:
        payload = {"status": "ok", "metrics_version": 11}

        client = TestClient(app)
        token = get_settings().api_token
        with (
            patch("tactix.get_dashboard__api._get_cached_dashboard_payload", return_value=payload),
            patch("tactix.get_dashboard__api.get_dashboard_payload") as get_payload,
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
