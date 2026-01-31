from __future__ import annotations

from tactix.config import Settings, get_settings
from tactix.db.duckdb_store import (
    fetch_metrics,
    get_connection,
    init_schema,
    update_metrics_summary,
    write_metrics_version,
)
from tactix.emit_progress__pipeline import _emit_progress
from tactix.pipeline_state__pipeline import ProgressCallback


def run_refresh_metrics(
    settings: Settings | None = None,
    source: str | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, object]:
    settings = settings or get_settings(source=source)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.ensure_dirs()

    _emit_progress(
        progress,
        "start",
        source=settings.source,
        message="Refreshing metrics",
    )

    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    update_metrics_summary(conn)
    metrics_version = write_metrics_version(conn)
    settings.metrics_version_file.write_text(str(metrics_version))

    _emit_progress(
        progress,
        "metrics_refreshed",
        source=settings.source,
        metrics_version=metrics_version,
        message="Metrics refreshed",
    )

    return {
        "source": settings.source,
        "user": settings.user,
        "metrics_version": metrics_version,
        "metrics_rows": len(fetch_metrics(conn, source=settings.source)),
    }
