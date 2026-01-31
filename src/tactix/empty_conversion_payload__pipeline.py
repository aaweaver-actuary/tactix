from __future__ import annotations

from tactix.config import Settings


def _empty_conversion_payload(settings: Settings) -> dict[str, object]:
    return {
        "source": settings.source,
        "games": 0,
        "inserted_games": 0,
        "positions": 0,
    }
