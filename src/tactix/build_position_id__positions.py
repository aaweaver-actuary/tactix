"""Build stable position identifiers from FEN and side-to-move."""

from __future__ import annotations

from tactix.utils import hash as hash_string


def _build_position_id(fen: str, side_to_move: str) -> int:
    """Return a stable integer hash for the given FEN and side-to-move."""
    if not fen:
        raise ValueError("Position FEN is required to build a position id.")
    if not side_to_move:
        raise ValueError("Position side-to-move is required to build a position id.")
    payload = f"{fen}|{side_to_move.lower()}"
    digest = hash_string(payload)
    return int(digest[:16], 16) & 0x7FFFFFFFFFFFFFFF


__all__ = ["_build_position_id"]
