from __future__ import annotations

from tactix.extract_status_code__lichess_client import _extract_status_code


def _is_auth_error(exc: BaseException) -> bool:
    """Check whether an exception represents an auth error.

    Args:
        exc: Exception raised by the API.

    Returns:
        True for auth errors, otherwise False.
    """

    status_code = _extract_status_code(exc)
    return status_code in {401, 403}
