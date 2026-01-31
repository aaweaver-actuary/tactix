from __future__ import annotations

from tactix.black_profiles_for_source__pipeline import _black_profiles_for_source
from tactix.config import Settings
from tactix.normalized_profile_for_source__pipeline import _normalized_profile_for_source
from tactix.side_filter_for_profile__pipeline import _side_filter_for_profile
from tactix.utils.normalize_string import normalize_string


def _resolve_side_to_move_filter(settings: Settings) -> str | None:
    source = normalize_string(settings.source)
    profile = _normalized_profile_for_source(settings, source)
    black_profiles = _black_profiles_for_source(source)
    if not profile or black_profiles is None:
        return None
    return _side_filter_for_profile(profile, black_profiles)
