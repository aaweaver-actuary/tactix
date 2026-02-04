"""Parse user move UCI strings into chess moves."""

import chess

from tactix.analyze_tactics__positions import logger
from tactix.utils.logger import funclogger


@funclogger
def _parse_user_move(board: chess.Board, user_move_uci: str, fen: str) -> chess.Move | None:
    try:
        user_move = chess.Move.from_uci(user_move_uci)
    except ValueError:
        logger.warning("Invalid UCI move %s; skipping position", user_move_uci)
        return None
    if user_move not in board.legal_moves:
        logger.warning("Illegal move %s for FEN %s", user_move_uci, fen)
        return None
    return user_move
