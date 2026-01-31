from __future__ import annotations


def _side_filter_for_profile(profile: str, black_profiles: set[str]) -> str | None:
    return "black" if profile in black_profiles else None
