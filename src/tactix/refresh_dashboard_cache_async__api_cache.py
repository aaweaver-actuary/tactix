"""Refresh dashboard cache in a background thread."""

from __future__ import annotations

from threading import Thread

from tactix.api_logger__tactix import logger
from tactix.dashboard_query import DashboardQuery
from tactix.prime_dashboard_cache__api_cache import _prime_dashboard_cache


def _refresh_dashboard_cache_async(sources: list[str | None]) -> None:
    def worker() -> None:
        for source in sources:
            try:
                _prime_dashboard_cache(DashboardQuery(source=source))
            except (RuntimeError, ValueError, TypeError):  # pragma: no cover - defensive
                logger.exception("Failed to prime dashboard cache", extra={"source": source})

    Thread(target=worker, daemon=True).start()
