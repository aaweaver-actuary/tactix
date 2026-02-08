"""Resolve user fields from PGN headers."""

from __future__ import annotations

from collections.abc import Mapping

import chess.pgn

from tactix._get_game_result_for_user_from_pgn_headers import (
    _get_game_result_for_user_from_pgn_headers,
)
from tactix._get_user_color_from_pgn_headers import _get_user_color_from_pgn_headers
from tactix.chess_game_result import ChessGameResult
from tactix.chess_player_color import ChessPlayerColor

_USER_COLOR_LABELS = {
    ChessPlayerColor.WHITE: "white",
    ChessPlayerColor.BLACK: "black",
}
_OPP_RATING_KEYS = {
    ChessPlayerColor.WHITE: "black_elo",
    ChessPlayerColor.BLACK: "white_elo",
}


def _resolve_user_fields__pgn_headers(
    headers: chess.pgn.Headers | None,
    metadata: Mapping[str, object],
    user: str,
) -> tuple[str | None, object | None, str]:
    """Return user color, opponent rating, and result values."""
    if headers is None:
        return None, None, ChessGameResult.UNKNOWN.value
    try:
        color = _get_user_color_from_pgn_headers(headers, user)
    except ValueError:
        return None, None, ChessGameResult.UNKNOWN.value
    result = _get_game_result_for_user_from_pgn_headers(headers, user).value
    return _USER_COLOR_LABELS[color], metadata.get(_OPP_RATING_KEYS[color]), result
