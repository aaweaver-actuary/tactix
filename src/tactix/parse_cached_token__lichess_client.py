from __future__ import annotations

from tactix.parse_cached_payload__lichess_client import _parse_cached_payload


def _parse_cached_token(raw: str) -> str | None:
    payload = _parse_cached_payload(raw)
    if payload is None:
        return raw
    token = payload.get("access_token")
    return str(token) if token else None
