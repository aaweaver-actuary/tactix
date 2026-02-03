from __future__ import annotations

from tactix.config import Settings


def _build_conversion_payload(
    settings: Settings,
    *,
    games: int,
    inserted_games: int,
    positions: int,
) -> dict[str, object]:
    return {
        "source": settings.source,
        "games": games,
        "inserted_games": inserted_games,
        "positions": positions,
    }


def _conversion_payload(
    settings: Settings,
    raw_pgns: list[dict[str, object]],
    to_process: list[dict[str, object]],
    positions: list[dict[str, object]],
) -> dict[str, object]:
    return _build_conversion_payload(
        settings,
        games=len(raw_pgns),
        inserted_games=len(to_process),
        positions=len(positions),
    )
