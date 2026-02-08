"""Update metrics summary and version counters."""

from __future__ import annotations

from tactix.config import Settings
from tactix.db.duckdb_store import write_metrics_version
from tactix.db.metrics_repository_provider import update_metrics_summary


def _update_metrics_and_version(settings: Settings, conn) -> int:
    update_metrics_summary(conn)
    metrics_version = write_metrics_version(conn)
    settings.metrics_version_file.write_text(str(metrics_version))
    return metrics_version
