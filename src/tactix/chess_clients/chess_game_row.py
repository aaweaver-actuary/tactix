"""Models and helpers for chess game rows."""

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import cast

from pydantic import BaseModel

from tactix.chess_clients.GameRowInputs import GameRowInputs


class ChessGameRow(BaseModel):
    """Represents a normalized chess game row.

    Attributes:
        game_id: Stable identifier for the game.
        user: Username associated with the game.
        source: Data source (e.g., "lichess" or "chesscom").
        fetched_at: Timestamp when the game was fetched.
        pgn: Raw PGN text.
        last_timestamp_ms: Last move timestamp in milliseconds.
    """

    game_id: str
    user: str
    source: str
    fetched_at: datetime
    pgn: str
    last_timestamp_ms: int


def build_game_row_dict[T: "ChessGameRow"](
    inputs: "GameRowInputs[T]",
) -> dict[str, object]:
    """Build a normalized game row dictionary from inputs."""
    fetched_at = datetime.now(UTC) if inputs.fetched_at is None else inputs.fetched_at
    model_cls = inputs.model_cls or cast(type[T], ChessGameRow)
    row = ChessGameRow(
        game_id=inputs.game_id,
        user=inputs.user,
        source=inputs.source,
        fetched_at=fetched_at,
        pgn=inputs.pgn,
        last_timestamp_ms=inputs.last_timestamp_ms,
    )
    return coerce_game_row_dict(row, model_cls=model_cls)


def coerce_game_row_dict[T: "ChessGameRow"](
    row: ChessGameRow,
    *,
    model_cls: type[T] | None = None,
) -> dict[str, object]:
    """Coerce a game row to the specified model and return a dict."""
    if model_cls is None:
        model_cls = cast(type[T], ChessGameRow)
    return model_cls.model_validate(row.model_dump()).model_dump()


def coerce_game_rows[T: "ChessGameRow"](
    rows: Iterable[dict],
    model_cls: type[T],
) -> list[dict]:
    """Coerce multiple row dicts to a model and return dicts."""
    return [model_cls.model_validate(row).model_dump() for row in rows]


def coerce_rows_for_model[T: "ChessGameRow"](
    model_cls: type[T],
) -> Callable[[Iterable[dict]], list[dict]]:
    """Return a helper that coerces rows to the model class."""

    def _coerce(rows: Iterable[dict]) -> list[dict]:
        return coerce_game_rows(rows, model_cls)

    return _coerce
