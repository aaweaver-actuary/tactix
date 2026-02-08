"""Push a move and return None for helper flows."""

import chess


def _push_and_none(board: chess.Board, move: chess.Move) -> None:
    """Push the move on the board."""
    board.push(move)
