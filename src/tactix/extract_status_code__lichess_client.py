from __future__ import annotations


def _extract_status_code(exc: BaseException) -> int | None:
    """Extract status codes from Lichess API exceptions.

    Args:
        exc: Exception raised by the API.

    Returns:
        Status code if available.
    """

    for attr in ("status", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    return status_code if isinstance(status_code, int) else None
