"""Validate raw PGN hash matches and raise on mismatch."""

from __future__ import annotations

from collections.abc import Mapping


def _raise_for_hash_mismatch(
    source: str,
    computed: Mapping[str, str],
    stored: Mapping[str, str],
    matched: int,
) -> None:
    """Raise a ValueError when computed and stored hashes diverge."""
    if matched == len(computed):
        return
    missing = [game_id for game_id, pgn_hash in computed.items() if stored.get(game_id) != pgn_hash]
    missing_sorted = ", ".join(sorted(missing))
    raise ValueError(
        f"Raw PGN hash mismatch for source={source} expected={len(computed)} "
        f"matched={matched} missing={missing_sorted}"
    )
