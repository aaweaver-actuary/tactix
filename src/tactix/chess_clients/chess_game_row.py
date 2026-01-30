from collections.abc import Iterable
from datetime import UTC, datetime
from typing import cast

from pydantic import BaseModel


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
    *,
    game_id: str,
    pgn: str,
    last_timestamp_ms: int,
    user: str,
    source: str,
    fetched_at: datetime | None = None,
    model_cls: type[T] | None = None,
) -> dict[str, object]:
    if fetched_at is None:
        fetched_at = datetime.now(UTC)
    if model_cls is None:
        model_cls = cast(type[T], ChessGameRow)
    row = ChessGameRow(
        game_id=game_id,
        user=user,
        source=source,
        fetched_at=fetched_at,
        pgn=pgn,
        last_timestamp_ms=last_timestamp_ms,
    )
    return coerce_game_row_dict(row, model_cls=model_cls)


def coerce_game_row_dict[T: "ChessGameRow"](
    row: ChessGameRow,
    *,
    model_cls: type[T] | None = None,
) -> dict[str, object]:
    if model_cls is None:
        model_cls = cast(type[T], ChessGameRow)
    return model_cls.model_validate(row.model_dump()).model_dump()


def coerce_game_rows[T: "ChessGameRow"](
    rows: Iterable[dict],
    model_cls: type[T],
) -> list[dict]:
    return [model_cls.model_validate(row).model_dump() for row in rows]
