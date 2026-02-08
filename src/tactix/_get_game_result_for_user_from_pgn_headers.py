"""Resolve PGN game results for a specific user."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import chess
import chess.pgn

from tactix._get_user_color_from_pgn_headers import _get_user_color_from_pgn_headers
from tactix.chess_game_result import ChessGameResult
from tactix.chess_player_color import ChessPlayerColor
from tactix.utils.logger import funclogger

if TYPE_CHECKING:
    from tactix.pgn_headers import PgnHeaders


@funclogger
def _get_game_result_for_user_from_pgn_headers(
    headers: chess.pgn.Headers | PgnHeaders,
    user: str,
) -> ChessGameResult:
    if _is_pgn_headers(headers):
        pgn_headers = cast("PgnHeaders", headers)
        return pgn_headers.result or ChessGameResult.UNKNOWN
    chess_headers = cast(chess.pgn.Headers, headers)
    result = _resolve_result_str(chess_headers)
    if result is None:
        return ChessGameResult.UNKNOWN
    color = _get_user_color_from_pgn_headers(chess_headers, user)
    return _resolve_game_result(result, color)


def _is_pgn_headers(headers: object) -> bool:
    return hasattr(headers, "result") and hasattr(headers, "white_player")


def _resolve_result_str(headers: chess.pgn.Headers) -> str | None:
    result = headers.get("Result")
    if result not in {"1-0", "0-1", "1/2-1/2"}:
        return None
    return result


def _resolve_game_result(result: str, color: ChessPlayerColor) -> ChessGameResult:
    try:
        return ChessGameResult.from_str(result, color)
    except ValueError:
        return ChessGameResult.UNKNOWN
