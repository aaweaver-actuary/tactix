"""Build canonical games table rows from raw game rows."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from io import StringIO

import chess.pgn

from tactix._empty_pgn_metadata import _empty_pgn_metadata
from tactix._extract_metadata_from_headers import _extract_metadata_from_headers
from tactix._get_game_result_for_user_from_pgn_headers import (
    _get_game_result_for_user_from_pgn_headers,
)
from tactix._get_user_color_from_pgn_headers import _get_user_color_from_pgn_headers
from tactix.chess_player_color import ChessPlayerColor
from tactix.chess_time_control import normalize_time_control_label


def _build_games_table_row(row: Mapping[str, object]) -> dict[str, object]:
    """Return a canonical games table row for a raw game row."""
    pgn = str(row.get("pgn") or "")
    user = str(row.get("user") or "")
    metadata, headers = _load_pgn_metadata(pgn, user)
    user_color, opp_rating, result = _resolve_user_metadata(headers, metadata, user)
    last_timestamp_ms = row.get("last_timestamp_ms")
    played_at = _resolve_played_at(metadata.get("start_timestamp_ms"), last_timestamp_ms)

    return {
        "game_id": str(row.get("game_id") or ""),
        "source": str(row.get("source") or ""),
        "user": user,
        "user_id": user,
        "user_color": user_color,
        "user_rating": metadata.get("user_rating"),
        "opp_rating": opp_rating,
        "result": result,
        "time_control": normalize_time_control_label(metadata.get("time_control")),
        "played_at": played_at,
        "pgn": pgn,
        "fetched_at": row.get("fetched_at"),
        "ingested_at": _resolve_ingested_at(row.get("ingested_at")),
        "last_timestamp_ms": last_timestamp_ms,
        "cursor": row.get("cursor"),
    }


def _load_pgn_metadata(
    pgn: str,
    user: str,
) -> tuple[dict[str, object], chess.pgn.Headers | None]:
    """Return parsed PGN metadata and headers."""
    metadata = _empty_pgn_metadata()
    if not pgn.strip().startswith("["):
        return metadata, None
    game = chess.pgn.read_game(StringIO(pgn))
    if not game or getattr(game, "errors", None):
        return metadata, None
    headers = game.headers
    return _extract_metadata_from_headers(headers, user), headers


def _resolve_user_metadata(
    headers: chess.pgn.Headers | None,
    metadata: Mapping[str, object],
    user: str,
) -> tuple[str | None, object | None, str | None]:
    """Return user color, opponent rating, and result values."""
    if headers is None:
        return None, None, None
    try:
        color = _get_user_color_from_pgn_headers(headers, user)
    except ValueError:
        return None, None, None
    if color == ChessPlayerColor.WHITE:
        user_color = "white"
        opp_rating = metadata.get("black_elo")
    else:
        user_color = "black"
        opp_rating = metadata.get("white_elo")
    result = _get_game_result_for_user_from_pgn_headers(headers, user).value
    return user_color, opp_rating, result


def _resolve_played_at(
    start_timestamp_ms: object,
    fallback_timestamp_ms: object,
) -> datetime | None:
    """Resolve the played_at timestamp from metadata or fallbacks."""
    timestamp_ms = _select_timestamp_ms(start_timestamp_ms, fallback_timestamp_ms)
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).replace(tzinfo=None)


def _select_timestamp_ms(primary: object, fallback: object) -> int | None:
    """Return the first valid timestamp in milliseconds."""
    for value in (primary, fallback):
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
    return None


def _resolve_ingested_at(value: object) -> datetime:
    """Return a UTC ingested timestamp when missing."""
    if isinstance(value, datetime):
        return value
    return datetime.now(UTC)


__all__ = ["_build_games_table_row"]
