"""Build conversion payloads for raw PGN ingestion."""

from __future__ import annotations

from tactix.config import Settings
from tactix.domain.conversion_payload import (
    build_conversion_payload,
    conversion_payload_from_lists,
)


def _build_conversion_payload(
    settings: Settings,
    *,
    games: int,
    inserted_games: int,
    positions: int,
) -> dict[str, object]:
    """Return a conversion payload summary."""
    return build_conversion_payload(
        settings.source,
        games=games,
        inserted_games=inserted_games,
        positions=positions,
    )


def _conversion_payload(
    settings: Settings,
    raw_pgns: list[dict[str, object]],
    to_process: list[dict[str, object]],
    positions: list[dict[str, object]],
) -> dict[str, object]:
    """Return a conversion payload using list lengths."""
    return conversion_payload_from_lists(
        settings.source,
        raw_pgns=raw_pgns,
        to_process=to_process,
        positions=positions,
    )
