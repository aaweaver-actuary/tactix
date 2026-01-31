from __future__ import annotations

from tactix.config import Settings
from tactix.pipeline_state__pipeline import ZERO_COUNT
from tactix.sync_postgres_analysis_results__pipeline import _sync_postgres_analysis_results


def _maybe_sync_analysis_results(
    conn,
    settings: Settings,
    pg_conn,
    analysis_pg_enabled: bool,
    postgres_written: int,
) -> tuple[int, int]:
    if pg_conn is None or not analysis_pg_enabled or postgres_written != ZERO_COUNT:
        return 0, postgres_written
    postgres_synced = _sync_postgres_analysis_results(conn, pg_conn, settings)
    return postgres_synced, postgres_written + postgres_synced
