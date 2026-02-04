"""Build inserts for legacy raw PGN rows."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from tactix._hash_pgn_text import _hash_pgn_text
from tactix.extract_pgn_metadata import extract_pgn_metadata


def _build_legacy_raw_pgn_inserts(
    rows: Iterable[tuple[object, ...]],
) -> list[tuple[object, ...]]:
    """Return insert tuples for legacy raw PGN rows."""
    inserts: list[tuple[object, ...]] = []
    for idx, row in enumerate(rows, start=1):
        game_id, user, source, fetched_at, pgn, last_timestamp_ms, cursor = row
        pgn_text = str(pgn or "")
        metadata = extract_pgn_metadata(pgn_text, str(user or ""))
        inserts.append(
            (
                idx,
                game_id,
                user,
                source,
                fetched_at,
                pgn_text,
                _hash_pgn_text(pgn_text),
                1,
                metadata.get("user_rating"),
                metadata.get("time_control"),
                datetime.now(UTC),
                last_timestamp_ms,
                cursor,
            )
        )
    return inserts
