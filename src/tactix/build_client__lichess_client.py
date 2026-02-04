"""Build Lichess API clients."""

from __future__ import annotations

import berserk

from tactix.config import Settings
from tactix.resolve_access_token__lichess_client import _resolve_access_token


def build_client(settings: Settings) -> berserk.Client:
    """Build a Berserk client for the Lichess API.

    Args:
        settings: Settings for the request.

    Returns:
        Berserk client instance.
    """

    token = _resolve_access_token(settings)
    session = berserk.TokenSession(token)
    return berserk.Client(session=session)
