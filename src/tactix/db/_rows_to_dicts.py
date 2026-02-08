"""Convert DuckDB query results to dictionaries."""

from __future__ import annotations

import duckdb


def _rows_to_dicts(
    result: duckdb.DuckDBPyConnection | duckdb.DuckDBPyRelation,
) -> list[dict[str, object]]:
    """Return rows as a list of dictionaries."""
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
