"""Shared SQL builders for raw PGN queries."""


def latest_raw_pgns_query(where_clause: str = "") -> str:
    """Return the latest raw PGN subquery with an optional WHERE clause."""
    return f"""
        SELECT * EXCLUDE (rn)
        FROM (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY game_id, source
                    ORDER BY pgn_version DESC
                ) AS rn
            FROM raw_pgns
            {where_clause}
        )
        WHERE rn = 1
    """
