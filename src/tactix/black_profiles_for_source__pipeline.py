"""Resolve blacklisted profiles by source."""

from __future__ import annotations

from tactix.define_pipeline_state__pipeline import (
    CHESSCOM_BLACK_PROFILES,
    LICHESS_BLACK_PROFILES,
)


def _black_profiles_for_source(source: str) -> set[str] | None:
    """Return blacklisted profiles for the given source."""
    if source == "lichess":
        return LICHESS_BLACK_PROFILES
    if source == "chesscom":
        return CHESSCOM_BLACK_PROFILES
    return None
