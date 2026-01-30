from __future__ import annotations

import requests


def prepare_error__http_status(response: requests.Response, context: str) -> None:
    """Raise a RuntimeError when an HTTP response is not OK.

    Args:
        response: HTTP response to inspect.
        context: Error context to include in the message.
    """
    if response.ok:
        return
    message = f"{context}: {response.status_code} {response.text.strip()}"
    raise RuntimeError(message.strip())
