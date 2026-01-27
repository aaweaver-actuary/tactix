import unittest
from datetime import date

from starlette.requests import Request

from tactix.api import _coerce_date_to_datetime, _extract_api_token, _format_sse


def _make_request(headers: dict[str, str]) -> Request:
    header_bytes = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in headers.items()
    ]
    scope = {
        "type": "http",
        "path": "/api/dashboard",
        "method": "GET",
        "headers": header_bytes,
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "client": ("test", 1234),
    }
    return Request(scope)


class ApiHelperTests(unittest.TestCase):
    def test_extract_api_token_prefers_bearer(self) -> None:
        request = _make_request({"Authorization": "Bearer token-123"})
        self.assertEqual(_extract_api_token(request), "token-123")

    def test_extract_api_token_falls_back_to_api_key(self) -> None:
        request = _make_request({"X-API-Key": "key-456"})
        self.assertEqual(_extract_api_token(request), "key-456")

    def test_coerce_date_to_datetime_bounds(self) -> None:
        value = date(2024, 1, 2)
        start = _coerce_date_to_datetime(value)
        end = _coerce_date_to_datetime(value, end_of_day=True)

        self.assertEqual(start.date(), value)
        self.assertEqual(start.time().hour, 0)
        self.assertEqual(end.date(), value)
        self.assertEqual(end.time().hour, 23)

    def test_format_sse(self) -> None:
        payload = {"status": "ok"}
        data = _format_sse("progress", payload)

        self.assertIn(b"event: progress", data)
        self.assertIn(b'data: {"status": "ok"}', data)


if __name__ == "__main__":
    unittest.main()
