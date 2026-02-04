import duckdb

from tactix.db._rows_to_dicts import _rows_to_dicts
from tactix.db.query_helpers import apply_limit_clause
from tactix.db.raw_pgns_queries import latest_raw_pgns_query


def fetch_latest_raw_pgns(
    conn: duckdb.DuckDBPyConnection,
    source: str | None = None,
    limit: int | None = None,
) -> list[dict[str, object]]:
    params: list[object] = []
    filters = []
    if source:
        filters.append("source = ?")
        params.append(source)
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    limit_clause = apply_limit_clause(params, limit)
    result = conn.execute(
        f"""
        {latest_raw_pgns_query(where_clause)}
        ORDER BY last_timestamp_ms DESC, game_id
        {limit_clause}
        """,
        params,
    )
    return _rows_to_dicts(result)
