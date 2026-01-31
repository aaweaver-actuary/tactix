import chess

from tactix.utils import funclogger


@funclogger
def get_material_value(piece_type: chess.PieceType | str) -> int:
    """Get the material value of a given piece type."""
    if isinstance(piece_type, str):
        piece_type = chess.PIECE_SYMBOLS.index(piece_type.lower())
    return {
        chess.PAWN: 100,
        chess.KNIGHT: 300,
        chess.BISHOP: 300,
        chess.ROOK: 500,
        chess.QUEEN: 900,
    }.get(piece_type, 0)
