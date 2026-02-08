"""Resolve player colors from PGN headers."""

from __future__ import annotations

from functools import singledispatch
from typing import TYPE_CHECKING

import chess
import chess.pgn

from tactix._normalize_player_name import _normalize_player_name
from tactix.chess_player_color import ChessPlayerColor
from tactix.utils.logger import funclogger

if TYPE_CHECKING:
    from tactix.pgn_headers import PgnHeaders


@funclogger
def _get_user_color_from_pgn_headers(
    headers: chess.pgn.Headers | PgnHeaders, user: str
) -> ChessPlayerColor:
    """Return the user's color from PGN headers."""
    white, black = _resolve_player_names(headers)
    return _resolve_user_color(white, black, user)


@singledispatch
def _resolve_player_names(headers: object) -> tuple[str, str]:
    """Resolve player names from a headers object."""
    white = getattr(headers, "white_player", None)
    black = getattr(headers, "black_player", None)
    return _normalize_player_name(white), _normalize_player_name(black)


@_resolve_player_names.register
def _resolve_player_names_from_headers(headers: chess.pgn.Headers) -> tuple[str, str]:
    """Resolve player names from standard PGN headers."""
    white = headers.get("White")
    black = headers.get("Black")
    return _normalize_player_name(white), _normalize_player_name(black)


def _resolve_user_color(white: str, black: str, user: str) -> ChessPlayerColor:
    """Return the player's color based on header names."""
    user_lower = _normalize_player_name(user)
    if _matches_user_color(white, user_lower):
        return ChessPlayerColor.WHITE
    if _matches_user_color(black, user_lower):
        return ChessPlayerColor.BLACK
    raise ValueError(f"User '{user}' not found in PGN headers.")


def _matches_user_color(player: str, user_lower: str) -> bool:
    return bool(player) and player == user_lower


_VULTURE_USED = (_resolve_player_names_from_headers,)
