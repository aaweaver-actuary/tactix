"""Extract metadata from PGN headers."""

from io import StringIO

import chess.pgn

from tactix._empty_pgn_metadata import _empty_pgn_metadata
from tactix._extract_metadata_from_headers import _extract_metadata_from_headers


def extract_pgn_metadata(pgn: str, user: str) -> dict[str, object]:
    """Return parsed metadata for a PGN and user."""
    if not pgn.strip().startswith("["):
        return _empty_pgn_metadata()
    game = chess.pgn.read_game(StringIO(pgn))
    if not game or getattr(game, "errors", None):
        return _empty_pgn_metadata()
    return _extract_metadata_from_headers(game.headers, user)
