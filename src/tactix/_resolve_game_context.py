"""Resolve a parsed PGN game context for extraction."""

import chess
import chess.pgn

from tactix.PgnContext import PgnContext
from tactix.position_context_builder import DEFAULT_POSITION_CONTEXT_BUILDER, logger


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
    user_color = DEFAULT_POSITION_CONTEXT_BUILDER.get_user_color(ctx.white, ctx.user)
    return game, board, user_color
