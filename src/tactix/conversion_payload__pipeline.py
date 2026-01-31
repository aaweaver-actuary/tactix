from __future__ import annotations

from tactix.config import Settings


def _conversion_payload(
    settings: Settings,
    raw_pgns: list[dict[str, object]],
    to_process: list[dict[str, object]],
    positions: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "source": settings.source,
        "games": len(raw_pgns),
        "inserted_games": len(to_process),
        "positions": len(positions),
    }
