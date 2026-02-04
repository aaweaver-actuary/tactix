from dataclasses import dataclass
from typing import cast

import chess

from tactix._score_best_line__after_move import _score_best_line__after_move
from tactix.StockfishEngine import StockfishEngine
from tactix.utils.logger import funclogger


@dataclass(frozen=True)
class BestLineContext:
    board: chess.Board
    best_move: chess.Move | None
    user_move_uci: str
    after_cp: int
    engine: StockfishEngine
    mover_color: bool


def _resolve_best_line_context(
    context: BestLineContext | chess.Board,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> BestLineContext:
    if isinstance(context, BestLineContext):
        return context
    values = _init_best_line_values(kwargs)
    _apply_best_line_args(values, args)
    _ensure_best_line_required(values)
    return BestLineContext(
        board=context,
        best_move=cast(chess.Move | None, values["best_move"]),
        user_move_uci=cast(str, values["user_move_uci"]),
        after_cp=cast(int, values["after_cp"]),
        engine=cast(StockfishEngine, values["engine"]),
        mover_color=cast(bool, values["mover_color"]),
    )


def _init_best_line_values(kwargs: dict[str, object]) -> dict[str, object]:
    return {
        "best_move": kwargs.get("best_move"),
        "user_move_uci": kwargs.get("user_move_uci"),
        "after_cp": kwargs.get("after_cp"),
        "engine": kwargs.get("engine"),
        "mover_color": kwargs.get("mover_color"),
    }


def _apply_best_line_args(values: dict[str, object], args: tuple[object, ...]) -> None:
    ordered_keys = ("best_move", "user_move_uci", "after_cp", "engine", "mover_color")
    values.update(dict(zip(ordered_keys, args, strict=False)))


def _ensure_best_line_required(values: dict[str, object]) -> None:
    required = ("user_move_uci", "after_cp", "engine", "mover_color")
    if any(values[key] is None for key in required):
        raise TypeError("Missing required best-line context values")


@funclogger
def _compare_move__best_line(
    context: BestLineContext | chess.Board,
    *args: object,
    **kwargs: object,
) -> int | None:
    resolved = _resolve_best_line_context(context, args, kwargs)
    if resolved.best_move is None or resolved.user_move_uci == resolved.best_move.uci():
        return None
    best_after_cp = _score_best_line__after_move(
        resolved.board,
        resolved.best_move,
        resolved.engine,
        resolved.mover_color,
    )
    if best_after_cp is None:
        return None
    return resolved.after_cp - best_after_cp
