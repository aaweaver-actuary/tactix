"""Normalize profile values in settings."""

from tactix._resolve_profile_value__settings import _resolve_profile_value__settings
from tactix.config import Settings
from tactix.utils.logger import funclogger


@funclogger
def _normalize_profile__settings(settings: Settings) -> str:
    profile_value = _resolve_profile_value__settings(settings)
    return profile_value.strip().lower()
