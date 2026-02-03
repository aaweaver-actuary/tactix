from __future__ import annotations

from datetime import UTC, datetime

from tactix.chess_clients.chess_game_row import build_game_row_dict
from tactix.coerce_pgn_text__lichess_client import _coerce_pgn_text
from tactix.config import Settings
from tactix.define_lichess_game_row__lichess_client import LichessGameRow
from tactix.extract_game_id import extract_game_id
from tactix.extract_last_timestamp_ms import extract_last_timestamp_ms


def _pgn_to_game_row(pgn: object, settings: Settings) -> dict | None:
    """Convert a PGN payload into a game row.

    Args:
        pgn: PGN payload from the API.
        settings: Settings for the request.

    Returns:
        Game row dictionary or None when empty.
    """

    if pgn is None:
        return None
    pgn_text = _coerce_pgn_text(pgn)
    game_id = extract_game_id(pgn_text)
    last_ts = extract_last_timestamp_ms(pgn_text)
    return build_game_row_dict(
        game_id=game_id,
        pgn=pgn_text,
        last_timestamp_ms=last_ts,
        user=settings.user,
        source=settings.source,
        fetched_at=datetime.now(UTC),
        model_cls=LichessGameRow,
    )
