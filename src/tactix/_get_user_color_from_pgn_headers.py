from __future__ import annotations

from functools import singledispatch
from typing import TYPE_CHECKING

import chess
import chess.pgn

from tactix.chess_player_color import ChessPlayerColor
from tactix.utils.logger import funclogger

if TYPE_CHECKING:
    from tactix.pgn_headers import PgnHeaders


@funclogger
def _get_user_color_from_pgn_headers(
    headers: chess.pgn.Headers | PgnHeaders, user: str
) -> ChessPlayerColor:
    white, black = _resolve_player_names(headers)
    return _resolve_user_color(white, black, user)


@singledispatch
def _resolve_player_names(headers: object) -> tuple[str, str]:
    white = getattr(headers, "white_player", None) or ""
    black = getattr(headers, "black_player", None) or ""
    return white.lower(), black.lower()


@_resolve_player_names.register
def _resolve_player_names_from_headers(headers: chess.pgn.Headers) -> tuple[str, str]:
    white = headers.get("White") or ""
    black = headers.get("Black") or ""
    return white.lower(), black.lower()


def _resolve_user_color(white: str, black: str, user: str) -> ChessPlayerColor:
    user_lower = user.lower()
    is_white = white == user_lower
    is_black = black == user_lower
    if not is_white and not is_black:
        raise ValueError(f"User '{user}' not found in PGN headers.")
    return ChessPlayerColor.WHITE if is_white else ChessPlayerColor.BLACK


_VULTURE_USED = (_resolve_player_names_from_headers,)
