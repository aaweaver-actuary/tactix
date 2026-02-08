"""API endpoint that returns the configured auth token."""

from __future__ import annotations

from tactix.config import get_settings


def auth_token() -> dict[str, str]:
    """Return the current API token payload."""
    settings = get_settings()
    return {
        "status": "ok",
        "token": settings.api_token,
        "token_type": "bearer",
        "user": settings.user,
    }
