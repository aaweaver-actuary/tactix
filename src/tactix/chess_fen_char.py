from enum import StrEnum


class ChessFenChar(StrEnum):
    """
    Enumeration representing the valid FEN (Forsyth-Edwards Notation) characters for chess pieces.

    Members:
        P: White pawn
        N: White knight
        B: White bishop
        R: White rook
        Q: White queen
        K: White king
        p: Black pawn
        n: Black knight
        b: Black bishop
        r: Black rook
        q: Black queen
        k: Black king

    Methods:
        is_valid(fen_char: str) -> bool:
            Checks if the given character is a valid FEN character for a chess piece.
    """

    P = "P"
    N = "N"
    B = "B"
    R = "R"
    Q = "Q"
    K = "K"
    p = "p"
    n = "n"
    b = "b"
    r = "r"
    q = "q"
    k = "k"

    @staticmethod
    def is_valid(fen_char: str) -> bool:
        return fen_char in ChessFenChar


_VULTURE_USED = (
    ChessFenChar.P,
    ChessFenChar.N,
    ChessFenChar.B,
    ChessFenChar.R,
    ChessFenChar.Q,
    ChessFenChar.K,
    ChessFenChar.p,
    ChessFenChar.n,
    ChessFenChar.b,
    ChessFenChar.r,
    ChessFenChar.q,
    ChessFenChar.k,
)
