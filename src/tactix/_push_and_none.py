import chess


def _push_and_none(board: chess.Board, move: chess.Move) -> None:
    board.push(move)
