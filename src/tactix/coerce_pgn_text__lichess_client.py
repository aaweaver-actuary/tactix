from __future__ import annotations


def _coerce_pgn_text(pgn: object) -> str:
    """Coerce PGN payloads to text.

    Args:
        pgn: PGN payload from the API.

    Returns:
        PGN text.
    """

    if isinstance(pgn, (bytes, bytearray)):
        return pgn.decode("utf-8", errors="replace")
    return str(pgn)
