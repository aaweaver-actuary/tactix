"""Convert best UCI move to SAN from a FEN position."""

import chess


def _best_san_from_fen(fen: str | None, best_uci: str) -> str | None:
    """Return SAN for the best UCI move when possible."""
    if not fen:
        return None
    try:
        board = chess.Board(str(fen))
        move = chess.Move.from_uci(best_uci)
        return board.san(move) if move in board.legal_moves else None
    except (ValueError, AssertionError):
        return None
