"""Count matching hashes between computed and stored maps."""

from __future__ import annotations

from collections.abc import Mapping


def _count_hash_matches(computed: Mapping[str, str], stored: Mapping[str, str]) -> int:
    return sum(1 for game_id, pgn_hash in computed.items() if stored.get(game_id) == pgn_hash)
