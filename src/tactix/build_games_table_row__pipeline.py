"""Build canonical games table rows from raw game rows."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from io import StringIO

import chess.pgn

from tactix._empty_pgn_metadata import _empty_pgn_metadata
from tactix._extract_metadata_from_headers import _extract_metadata_from_headers
from tactix.chess_time_control import normalize_time_control_label
from tactix.resolve_user_fields__pgn_headers import _resolve_user_fields__pgn_headers


def _build_games_table_row(row: Mapping[str, object]) -> dict[str, object]:
    """Return a canonical games table row for a raw game row."""
    fields = _coerce_row_fields(row)
    metadata, headers = _load_pgn_metadata(fields["pgn"], fields["user"])
    user_color, opp_rating, result = _resolve_user_fields__pgn_headers(
        headers, metadata, fields["user"]
    )
    played_at = _resolve_played_at(metadata.get("start_timestamp_ms"), fields["last_timestamp_ms"])
    resolved = _resolve_user_fields_payload(user_color, opp_rating, result, played_at)
    return _assemble_games_table_row(fields, metadata, resolved)


def _coerce_row_fields(row: Mapping[str, object]) -> dict[str, object]:
    """Return normalized input fields from a raw game row."""
    return {
        "game_id": str(row.get("game_id") or ""),
        "source": str(row.get("source") or ""),
        "user": str(row.get("user") or ""),
        "pgn": str(row.get("pgn") or ""),
        "fetched_at": row.get("fetched_at"),
        "ingested_at": row.get("ingested_at"),
        "last_timestamp_ms": row.get("last_timestamp_ms"),
        "cursor": row.get("cursor"),
    }


def _resolve_user_fields_payload(
    user_color: str | None,
    opp_rating: int | None,
    result: str,
    played_at: datetime | None,
) -> dict[str, object]:
    """Return resolved user fields for the games table row."""
    return {
        "user_color": user_color,
        "opp_rating": opp_rating,
        "result": result,
        "played_at": played_at,
    }


def _assemble_games_table_row(
    fields: dict[str, object],
    metadata: dict[str, object],
    resolved: dict[str, object],
) -> dict[str, object]:
    """Return a canonical games table row for storage."""
    return {
        "game_id": fields["game_id"],
        "source": fields["source"],
        "user": fields["user"],
        "user_id": fields["user"],
        "user_color": resolved["user_color"],
        "user_rating": metadata.get("user_rating"),
        "opp_rating": resolved["opp_rating"],
        "result": resolved["result"],
        "time_control": normalize_time_control_label(metadata.get("time_control")),
        "played_at": resolved["played_at"],
        "pgn": fields["pgn"],
        "fetched_at": fields["fetched_at"],
        "ingested_at": _resolve_ingested_at(fields["ingested_at"]),
        "last_timestamp_ms": fields["last_timestamp_ms"],
        "cursor": fields["cursor"],
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
