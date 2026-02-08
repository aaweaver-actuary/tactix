"""Resolve fork severity floor from settings."""

from tactix._is_profile_in import _is_profile_in
from tactix.analyze_tactics__positions import _SEVERITY_MAX
from tactix.config import Settings
from tactix.utils.logger import funclogger


@funclogger
def _fork_floor_for_settings(settings: Settings | None) -> float | None:
    """Resolve the fork severity floor if configured or implied by profile."""
    if settings is None:
        return None
    if settings.fork_severity_floor is not None:
        return settings.fork_severity_floor
    if _is_profile_in(settings, {"bullet"}):
        return _SEVERITY_MAX
    return None
