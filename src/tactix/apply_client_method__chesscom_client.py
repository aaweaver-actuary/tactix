"""Apply Chess.com client methods using settings."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tactix.build_client_for_settings__chesscom_client import _client_for_settings
from tactix.config import Settings


def _client_method[T](settings: Settings, method: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Instantiate a client and call the provided method."""
    client = _client_for_settings(settings)
    return method(client, *args, **kwargs)
