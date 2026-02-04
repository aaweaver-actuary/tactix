"""Upsert raw PGN rows into Postgres."""

from collections.abc import Mapping

from tactix._maybe_upsert_raw_pgn_row import _maybe_upsert_raw_pgn_row


def _upsert_postgres_raw_pgn_rows(
    cur,
    rows: list[Mapping[str, object]],
) -> int:
    """Upsert rows and return the number inserted."""
    latest_cache: dict[tuple[str, str], tuple[str | None, int]] = {}
    inserted = 0
    for row in rows:
        inserted += _maybe_upsert_raw_pgn_row(cur, row, latest_cache)
    return inserted
