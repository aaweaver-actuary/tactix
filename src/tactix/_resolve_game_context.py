"""Resolve a parsed PGN game context for extraction."""

import chess
import chess.pgn

from tactix._position_context_helpers import _get_user_color, logger
from tactix.PgnContext import PgnContext


def _resolve_game_context(ctx: PgnContext) -> tuple[chess.pgn.Game, chess.Board, bool] | None:
    game = ctx.game
    if not game:
        logger.warning("Unable to parse PGN")
        return None
    if ctx.user not in {ctx.white, ctx.black}:
        logger.info("User %s not present in game headers; skipping", ctx.user)
        return None
    board = ctx.board
    if board is None:
        logger.warning("Unable to build board for PGN")
        return None
    user_color = _get_user_color(ctx.white, ctx.user)
    return game, board, user_color
