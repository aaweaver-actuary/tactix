import chess
import chess.pgn

from tactix._position_from_node import _position_from_node
from tactix.PgnContext import PgnContext


def _iter_position_contexts(
    ctx: PgnContext,
    game: chess.pgn.Game,
    board: chess.Board,
    user_color: bool,
    side_filter: str | None,
) -> list[dict[str, object]]:
    positions: list[dict[str, object]] = []
    for node in game.mainline():
        position = _position_from_node(
            ctx,
            game,
            board,
            user_color,
            side_filter,
            node,
        )
        if position is not None:
            positions.append(position)
    return positions
