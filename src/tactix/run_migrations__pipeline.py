"""Run DuckDB schema migrations."""

from __future__ import annotations

from tactix.app.use_cases.pipeline_support import _emit_progress
from tactix.config import Settings, get_settings
from tactix.db.duckdb_store import get_connection, get_schema_version, migrate_schema
from tactix.define_pipeline_state__pipeline import ProgressCallback


def run_migrations(
    settings: Settings | None = None,
    source: str | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, object]:
    """Run migrations and return the resulting schema version."""
    settings = settings or get_settings(source=source)
    if source:
        settings.source = source
    settings.ensure_dirs()

    _emit_progress(
        progress,
        "migrations_start",
        source=settings.source,
        message="Starting DuckDB schema migrations",
    )

    conn = get_connection(settings.duckdb_path)
    migrate_schema(conn)
    schema_version = get_schema_version(conn)

    _emit_progress(
        progress,
        "migrations_complete",
        source=settings.source,
        schema_version=schema_version,
    )

    return {
        "source": settings.source,
        "schema_version": schema_version,
    }
