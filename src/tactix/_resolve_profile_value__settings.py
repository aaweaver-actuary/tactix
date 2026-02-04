"""Resolve the profile value for a settings object."""

from tactix._resolve_chesscom_profile_value import _resolve_chesscom_profile_value
from tactix.config import Settings
from tactix.utils.logger import funclogger


@funclogger
def _resolve_profile_value__settings(settings: Settings) -> str:
    """Return the resolved profile name for the given settings."""
    if settings.source == "chesscom":
        return _resolve_chesscom_profile_value(settings)
    return settings.lichess_profile or settings.rapid_perf
