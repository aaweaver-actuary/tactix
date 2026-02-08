"""Initialize analysis schema when Postgres is enabled."""

from __future__ import annotations

from tactix.init_analysis_schema import init_analysis_schema


def _init_analysis_schema_if_needed(pg_conn, analysis_pg_enabled: bool) -> None:
    if pg_conn is not None and analysis_pg_enabled:
        init_analysis_schema(pg_conn)
