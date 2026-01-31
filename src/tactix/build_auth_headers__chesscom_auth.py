from __future__ import annotations


def _auth_headers(token: str | None) -> dict[str, str]:
    """Build authorization headers.

    Args:
        token: API token if available.

    Returns:
        Headers dict for the request.
    """

    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}
