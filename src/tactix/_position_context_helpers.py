from __future__ import annotations

from dataclasses import asdict

import chess
import chess.pgn

from tactix._clock_from_comment import _clock_from_comment
from tactix.PgnContext import PgnContext
from tactix.PositionContext import PositionContext
from tactix.utils.logger import get_logger

logger = get_logger(__name__)


def _get_user_color(white: str, user: str) -> bool:
    return chess.WHITE if user.lower() == white.lower() else chess.BLACK


def _should_skip_for_turn(board: chess.Board, user_color: bool) -> bool:
    return board.turn != user_color


def _should_skip_for_side(side_to_move: str, side_filter: str | None) -> bool:
    return bool(side_filter and side_to_move != side_filter)


def _is_illegal_move(board: chess.Board, move: chess.Move) -> bool:
    return move not in board.legal_moves


def _side_from_turn(turn: bool) -> str:
    return "white" if turn == chess.WHITE else "black"


def _build_position_context(
    ctx: PgnContext,
    game: chess.pgn.Game,
    board: chess.Board,
    node: chess.pgn.ChildNode,
    move: chess.Move,
    side_to_move: str,
) -> dict[str, object]:
    return asdict(
        PositionContext(
            game_id=ctx.game_id or game.headers.get("Site", ""),
            user=ctx.user,
            source=ctx.source,
            fen=board.fen(),
            ply=board.ply(),
            move_number=board.fullmove_number,
            side_to_move=side_to_move,
            uci=move.uci(),
            san=board.san(move),
            clock_seconds=_clock_from_comment(node.comment or ""),
            is_legal=True,
        )
    )
