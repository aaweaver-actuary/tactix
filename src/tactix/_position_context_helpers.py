from __future__ import annotations

from dataclasses import asdict, dataclass

import chess
import chess.pgn

from tactix._clock_from_comment import _clock_from_comment
from tactix.PgnContext import PgnContext
from tactix.PositionContext import PositionContext
from tactix.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class PositionContextInputs:
    ctx: PgnContext
    game: chess.pgn.Game
    board: chess.Board
    node: chess.pgn.ChildNode
    move: chess.Move
    side_to_move: str


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
    inputs: PositionContextInputs,
) -> dict[str, object]:
    return asdict(
        PositionContext(
            game_id=inputs.ctx.game_id or inputs.game.headers.get("Site", ""),
            user=inputs.ctx.user,
            source=inputs.ctx.source,
            fen=inputs.board.fen(),
            ply=inputs.board.ply(),
            move_number=inputs.board.fullmove_number,
            side_to_move=inputs.side_to_move,
            user_to_move=True,
            uci=inputs.move.uci(),
            san=inputs.board.san(inputs.move),
            clock_seconds=_clock_from_comment(inputs.node.comment or ""),
            is_legal=True,
        )
    )
