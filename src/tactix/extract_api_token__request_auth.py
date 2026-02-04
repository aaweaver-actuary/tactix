"""Extract API tokens from request headers."""

from __future__ import annotations

from fastapi import Request


def _extract_api_token(request: Request) -> str | None:
    """Return bearer token or API key from the request headers."""
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key.strip()
    return None
