"""Delete position, tactic, outcome, and raw PGN rows for games."""

from __future__ import annotations

import duckdb


def delete_game_rows(conn: duckdb.DuckDBPyConnection, game_ids: list[str]) -> None:
    """Delete position, tactic, outcome, and raw PGN rows for the provided games."""
    if not game_ids:
        return
    placeholders = ", ".join(["?"] * len(game_ids))
    tactic_ids = conn.execute(
        f"SELECT tactic_id FROM tactics WHERE game_id IN ({placeholders})",
        game_ids,
    ).fetchall()
    tactic_id_values = [row[0] for row in tactic_ids]
    if tactic_id_values:
        outcome_placeholders = ", ".join(["?"] * len(tactic_id_values))
        conn.execute(
            f"DELETE FROM tactic_outcomes WHERE tactic_id IN ({outcome_placeholders})",
            tactic_id_values,
        )
    conn.execute(
        f"DELETE FROM tactics WHERE game_id IN ({placeholders})",
        game_ids,
    )
    conn.execute(
        f"DELETE FROM positions WHERE game_id IN ({placeholders})",
        game_ids,
    )
    conn.execute(
        f"DELETE FROM raw_pgns WHERE game_id IN ({placeholders})",
        game_ids,
    )
