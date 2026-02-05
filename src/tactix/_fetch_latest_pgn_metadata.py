"""Fetch the latest PGN metadata for a game."""

from tactix.define_db_schemas__const import PGN_SCHEMA


def _fetch_latest_pgn_metadata(
    cur,
    game_id: str,
    source: str,
) -> tuple[str | None, int]:
    """Return latest PGN hash/version for a game and source."""
    cur.execute(
        f"""
        SELECT pgn_hash, pgn_version
        FROM {PGN_SCHEMA}.raw_pgns
        WHERE game_id = %s AND source = %s
        ORDER BY pgn_version DESC
        LIMIT 1
        """,
        (game_id, source),
    )
    existing = cur.fetchone()
    if existing:
        return existing[0], int(existing[1] or 0)
    return None, 0
