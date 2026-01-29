import unittest
from unittest.mock import patch

from tactix.api import (
    _DASHBOARD_CACHE_TTL_S,
    _clear_dashboard_cache,
    _dashboard_cache_key,
    _get_cached_dashboard_payload,
    _set_dashboard_cache,
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

        with patch(
            "tactix.api.time_module.time", return_value=float(_DASHBOARD_CACHE_TTL_S + 1)
        ):
            cached = _get_cached_dashboard_payload(key)

        self.assertIsNone(cached)


if __name__ == "__main__":
    unittest.main()
