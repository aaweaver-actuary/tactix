from __future__ import annotations


def _is_latest_hash(latest_hash: str | None, pgn_hash: str) -> bool:
    return latest_hash == pgn_hash
