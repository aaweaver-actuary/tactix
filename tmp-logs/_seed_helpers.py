from tactix.db.duckdb_store import insert_positions


def _ensure_position(conn, position: dict[str, object]) -> dict[str, object]:
    row = conn.execute(
        """
        SELECT position_id, game_id, fen, uci
        FROM positions
        WHERE source = ?
          AND game_id = ?
          AND uci = ?
          AND fen = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        [position["source"], position["game_id"], position["uci"], position["fen"]],
    ).fetchone()
    if row:
        position["position_id"] = row[0]
        return position
    position_ids = insert_positions(conn, [position])
    position["position_id"] = position_ids[0]
    return position
