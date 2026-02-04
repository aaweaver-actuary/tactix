import duckdb

from tactix.db._rows_to_dicts import _rows_to_dicts
from tactix.db.query_helpers import apply_limit_clause


def fetch_unanalyzed_positions(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str] | None = None,
    source: str | None = None,
    limit: int | None = None,
) -> list[dict[str, object]]:
    params: list[object] = []
    filters: list[str] = ["t.position_id IS NULL"]
    if game_ids:
        placeholders = ", ".join(["?"] * len(game_ids))
        filters.append(f"p.game_id IN ({placeholders})")
        params.extend(game_ids)
    if source:
        filters.append("p.source = ?")
        params.append(source)
    where_clause = f"WHERE {' AND '.join(filters)}"
    limit_clause = apply_limit_clause(params, limit)
    result = conn.execute(
        f"""
        SELECT p.*
        FROM positions AS p
        LEFT JOIN tactics AS t
            ON p.position_id = t.position_id
        {where_clause}
        ORDER BY p.position_id
        {limit_clause}
        """,
        params,
    )
    return _rows_to_dicts(result)
