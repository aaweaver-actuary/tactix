from __future__ import annotations

from tactix.config import Settings


def _resolve_perf_value(settings: Settings) -> str:
    """Resolve the perf filter value for a Lichess request.

    Args:
        settings: Settings for the request.

    Returns:
        Perf value string.
    """

    return settings.lichess_profile or settings.rapid_perf
