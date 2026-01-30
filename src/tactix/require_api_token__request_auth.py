from __future__ import annotations

from fastapi import HTTPException, Request, status

from tactix.config import get_settings
from tactix.extract_api_token__request_auth import _extract_api_token


def require_api_token(request: Request) -> None:
    if request.url.path == "/api/health":
        return
    settings = get_settings()
    expected = settings.api_token
    supplied = _extract_api_token(request)
    if not supplied or supplied != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
