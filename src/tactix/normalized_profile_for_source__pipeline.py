from __future__ import annotations

from tactix.config import Settings


def _normalized_profile_for_source(settings: Settings, source: str) -> str:
    profiles = {
        "lichess": settings.lichess_profile or settings.rapid_perf,
        "chesscom": settings.chesscom.profile or settings.chesscom.time_class,
    }
    raw_profile = profiles.get(source)
    return (raw_profile or "").strip().lower()
