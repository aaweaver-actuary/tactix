from __future__ import annotations

import duckdb

from tactix.build_pipeline_settings__pipeline import _build_pipeline_settings
from tactix.config import Settings
from tactix.db.duckdb_store import fetch_latest_raw_pgns, get_connection, init_schema


def _prepare_raw_pgn_context(
    settings: Settings | None = None,
    source: str | None = None,
    profile: str | None = None,
    limit: int | None = None,
) -> tuple[Settings, duckdb.DuckDBPyConnection, list[dict[str, object]]]:
    settings = _build_pipeline_settings(settings, source=source, profile=profile)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    raw_pgns = fetch_latest_raw_pgns(conn, settings.source, limit)
    return settings, conn, raw_pgns
