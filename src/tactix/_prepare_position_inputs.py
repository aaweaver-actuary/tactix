import chess

from tactix.utils.logger import funclogger


@funclogger
def _prepare_position_inputs(
    position: dict[str, object],
) -> tuple[str, str, chess.Board, chess.Board, bool]:
    fen = str(position["fen"])
    user_move_uci = str(position["uci"])
    board = chess.Board(fen)
    motif_board = board.copy()
    mover_color = board.turn
    return fen, user_move_uci, board, motif_board, mover_color
