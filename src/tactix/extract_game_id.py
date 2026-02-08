"""Helpers for extracting game identifiers from PGNs."""

from io import StringIO

import chess.pgn

from tactix._extract_site_id import _extract_site_id


def extract_game_id(pgn: str) -> str:
    """Extract a stable game id from a PGN string."""
    game = chess.pgn.read_game(StringIO(pgn))
    return _extract_site_id(game) or str(abs(hash(pgn)))
