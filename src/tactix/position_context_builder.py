"""Build position contexts with an object-based API."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import chess
import chess.pgn

from tactix._clock_from_comment import _clock_from_comment
from tactix.PgnContext import PgnContext
from tactix.PositionContext import PositionContext
from tactix.utils.logger import Logger

logger = Logger(__name__)


@dataclass(frozen=True)
class PositionContextInputs:
    """Inputs required to build a position context."""

    ctx: PgnContext
    game: chess.pgn.Game
    board: chess.Board
    node: chess.pgn.ChildNode
    move: chess.Move
    side_to_move: str


class PositionContextBuilder:
    """Construct PositionContext payloads for extracted moves."""

    def __init__(self, log: Logger | None = None) -> None:
        self._logger = log or logger

    @property
    def log(self) -> Logger:
        """Return the logger for context builder warnings."""
        return self._logger

    def get_user_color(self, white: str, user: str) -> bool:
        """Return the user's color based on the white header."""
        return chess.WHITE if user.lower() == white.lower() else chess.BLACK

    def should_skip_for_turn(self, board: chess.Board, user_color: bool) -> bool:
        """Return True when the board turn does not match the user color."""
        return board.turn != user_color

    def should_skip_for_side(self, side_to_move: str, side_filter: str | None) -> bool:
        """Return True when a side filter excludes the current side."""
        return bool(side_filter and side_to_move != side_filter)

    def is_illegal_move(self, board: chess.Board, move: chess.Move) -> bool:
        """Return True when the move is not legal on the given board."""
        return move not in board.legal_moves

    def side_from_turn(self, turn: bool) -> str:
        """Return "white" or "black" from a board turn value."""
        return "white" if turn == chess.WHITE else "black"

    def build(self, inputs: PositionContextInputs) -> dict[str, object]:
        """Build a serialized PositionContext for downstream storage."""
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


DEFAULT_POSITION_CONTEXT_BUILDER = PositionContextBuilder()
