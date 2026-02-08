"""Domain rules for conversion payloads."""

from __future__ import annotations


def build_conversion_payload(
    source: str,
    *,
    games: int,
    inserted_games: int,
    positions: int,
) -> dict[str, object]:
    """Return a conversion payload summary."""
    return {
        "source": source,
        "games": games,
        "inserted_games": inserted_games,
        "positions": positions,
    }


def conversion_payload_from_lists(
    source: str,
    raw_pgns: list[dict[str, object]],
    to_process: list[dict[str, object]],
    positions: list[dict[str, object]],
) -> dict[str, object]:
    """Return a conversion payload using list lengths."""
    return build_conversion_payload(
        source,
        games=len(raw_pgns),
        inserted_games=len(to_process),
        positions=len(positions),
    )
