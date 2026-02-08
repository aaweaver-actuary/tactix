"""Hash PGN text using the base store helper."""

from tactix.define_base_db_store__db_store import BaseDbStore


def _hash_pgn_text(pgn: str) -> str:
    return BaseDbStore.hash_pgn(pgn)
