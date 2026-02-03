import chess
import pytest

from tactix.chess_piece import ChessPiece
from tactix.chess_fen_char import ChessFenChar
from tactix.chess_piece_type import ChessPieceType
from tactix.chess_player_color import ChessPlayerColor
from tactix.chess_time_control import (
    ChessTimeControl,
)


def test_chess_player_color_helpers() -> None:
    assert ChessPlayerColor.from_str("white") == ChessPlayerColor.WHITE
    assert ChessPlayerColor.from_str("b") == ChessPlayerColor.BLACK
    assert ChessPlayerColor.from_fen_char("P") == ChessPlayerColor.WHITE
    assert ChessPlayerColor.from_fen_char("p") == ChessPlayerColor.BLACK
    assert ChessPlayerColor.WHITE.is_white()
    assert ChessPlayerColor.BLACK.is_black()


def test_chess_piece_type_from_str_and_as_chess() -> None:
    assert ChessPieceType.from_str("q") == ChessPieceType.QUEEN
    assert ChessPieceType.from_str("Knight") == ChessPieceType.KNIGHT
    assert ChessPieceType.ROOK.as_chess() == chess.ROOK
    with pytest.raises(ValueError):
        ChessPieceType.from_str("invalid")


def test_chess_fen_char_and_piece_from_fen_char() -> None:
    assert ChessFenChar.is_valid("K")
    assert not ChessFenChar.is_valid("x")
    piece = ChessPiece.from_fen_char("n")
    assert piece.color == ChessPlayerColor.BLACK
    assert piece.piece == ChessPieceType.KNIGHT
    with pytest.raises(ValueError):
        ChessPiece.from_fen_char("x")


def test_chess_time_control_round_trip() -> None:
    tc = ChessTimeControl.from_pgn_string("300+5")
    assert tc is not None
    assert tc.initial == 300
    assert tc.increment == 5
    assert tc.as_str() == "300+5"
    assert str(tc) == "300+5"
    assert ChessTimeControl.from_pgn_string("600") == ChessTimeControl(initial=600, increment=None)
    assert ChessTimeControl.from_pgn_string("-") is None
