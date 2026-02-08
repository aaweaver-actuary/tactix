"""Check whether the current profile is in a set."""

from tactix._normalize_profile__settings import _normalize_profile__settings
from tactix.config import Settings
from tactix.utils.logger import funclogger


@funclogger
def _is_profile_in(settings: Settings, profiles: set[str]) -> bool:
    normalized = _normalize_profile__settings(settings)
    if not normalized:
        return False
    return normalized in {entry.strip().lower() for entry in profiles}
