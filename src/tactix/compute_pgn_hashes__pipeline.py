"""Compute PGN hashes for raw game rows."""

from __future__ import annotations

from tactix.db.duckdb_store import hash_pgn
from tactix.define_pipeline_state__pipeline import GameRow
from tactix.normalize_pgn import normalize_pgn


def _compute_pgn_hashes(rows: list[GameRow], source: str) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for row in rows:
        game_id = row["game_id"]
        if game_id in hashes:
            raise ValueError(f"Duplicate game_id in raw PGN batch for source={source}: {game_id}")
        normalized = normalize_pgn(row["pgn"])
        hashes[game_id] = hash_pgn(normalized if normalized is not None else row["pgn"])
    return hashes
